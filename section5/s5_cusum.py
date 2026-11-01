#!/usr/bin/env python3
"""CUSUM sanity detector on squared 5-min returns, and the alarm-vs-random-time volatility diagnostic. RAW fold 3, VALIDATION only; no selection.
Choices (author, user away): z_t = ret5_t^2 / mean(ret5^2 over the first REF=12 real grid bars of the SAME session) so the detector sees within-session change;
two-sided: S+ = max(0, S+ + z - 2), S- = max(0, S- + 0.5 - z); alarm when either >= h, no alarms before bar REF; confirmation = same side still >= h at the
third real update after the alarm (skip resets the count); 30-min refractory then S reset to 0. Variants: raw return, causal slot-deseasonalised return."""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_eval as V, s5_fast as F, s5_pilot as P, s5_events as E

N = 100; REF = 12; KU, KD = 2.0, 0.5
HS = [2, 3, 4, 6, 8, 12, 16, 24, 32, 48]
FAMS = ["gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"]


def detect_cusum(ret, real, avail, h, ref=REF, hold=3, refractory_min=30):
    n = len(ret); events = []; dropped = 0
    ok = real[:ref] & np.isfinite(ret[:ref])
    if n <= ref or ok.sum() < 8: return events, 0
    s2 = np.mean(ret[:ref][ok] ** 2)
    if not s2 > 0: return events, 0
    z = np.where(real & np.isfinite(ret), ret ** 2 / s2, np.nan)
    Sp = Sd = 0.0; cand = None; ref_until = -1
    for i in range(ref, n):
        if not np.isfinite(z[i]):
            if cand is not None: cand["count"] = 0
            continue
        Sp = max(0.0, Sp + z[i] - KU); Sd = max(0.0, Sd + KD - z[i])
        if avail[i] < ref_until: cand = None; continue
        if cand is not None:
            side = Sp if cand["side"] == "up" else Sd
            if side >= h:
                cand["count"] += 1
                if cand["count"] >= hold:
                    events.append(dict(i_d=cand["i_d"], i_c=i, state=0 if cand["side"] == "up" else 1)); ref_until = avail[i] + refractory_min * E.MIN; Sp = Sd = 0.0; cand = None
            else: cand = None
            continue
        if Sp >= h: cand = dict(side="up", i_d=i, count=0)
        elif Sd >= h: cand = dict(side="dn", i_d=i, count=0)
    if cand is not None: dropped += 1
    return events, dropped


def score(seqs, taus, h, is_break):
    c = 0
    for q, tau in zip(seqs, taus):
        ev = detect_cusum(q["X"][:, 0], np.isfinite(q["X"][:, 0]), q["avail"], h)[0]
        if is_break: c += any(tau <= q["avail"][e["i_c"]] <= tau + 60 * E.MIN for e in ev)
        else: c += bool(ev)
    return c / len(seqs)


def vol_ratio(r1, slot_d, w=30):
    sq = r1 ** 2; pre = sq[max(0, slot_d - w + 1):slot_d + 1]; post = sq[slot_d + 1:slot_d + 1 + w]
    if np.isfinite(pre).sum() < w // 2 or np.isfinite(post).sum() < w // 2 or not np.nanmean(pre) > 0: return np.nan
    return float(np.nanmean(post) / np.nanmean(pre))


def qs(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) == 0: return dict(n=0)
    return dict(n=int(len(x)), q10_25_50_75_90=[round(float(v), 2) for v in np.quantile(x, [.1, .25, .5, .75, .9])], share_gt1p5=round(float((x > 1.5).mean()), 2), share_lt_0p67=round(float((x < 1 / 1.5).mean()), 2))


def main():
    primary, _, _ = L.pools(); cols = primary; names = [L.RET_NAME] + cols
    d = L.load_era("RAW", cols + ["lee_mykland_approx60"]); seg = L.fold_segments(d, "RAW", 3)
    rows = {k: [L.session_grid(d, i, cols) for i in seg[k]] for k in ("train", "val")}; Mx = F.ret5_matrix(d, cols)
    rng = np.random.default_rng(P.SEED + 300); br_t, nu = V.sample_pairs(d, seg["val"], N, N, rng)
    rv, vol, n = V.session_stats(d, seg["val"]); fin = np.array([np.isfinite(d["close"][int(d["first"][i]):int(d["end"][i])]).mean() for i in seg["val"]])
    ok = (n == 390) & (fin >= 0.98); s = np.asarray(seg["val"])[ok]; rvv = rv[ok]; lo, hi = np.quantile(rvv, .1), np.quantile(rvv, .9)
    calm, stressed = s[rvv <= lo], s[rvv >= hi]; r2 = np.random.default_rng(P.SEED + 400); br_d = []
    for k in range(N):
        up = k % 2 == 0
        for _ in range(100):
            A = int(r2.choice(calm if up else stressed)); B = int(r2.choice(stressed if up else calm)); g = int(r2.choice(V.TAU_SLOTS)); fa, fb = int(d["first"][A]), int(d["first"][B])
            if np.isfinite(d["close"][[fa + g, fb + g, fb + g + 1]]).all() and d["valid"][fb + g + 1] and d["valid"][fb + g]: break
        br_d.append(dict(iA=A, iB=B, g=g, kind="calm_to_stressed" if up else "stressed_to_calm"))
    allr = F.splice_batch(br_t + br_d + nu, "RAW", cols, 4); bt, bd, nr = allr[:N], allr[N:2 * N], allr[2 * N:]
    out = dict(cusum={}, alarm_ratio={})

    def variant(var, r):
        return dict(avail=r["avail"], X=r["X"] if var == "raw" else F.deseason(r["X"], F.ret5_scale(Mx, r["iA"])))

    # ---- (1) CUSUM table
    for var in ("raw", "des"):
        sq = {k: [variant(var, r) for r in rr] for k, rr in (("t", bt), ("d", bd), ("n", nr))}
        out["cusum"][var] = {str(h): dict(fa=score(sq["n"], [0] * N, h, False), hit_tercile=score(sq["t"], [r["tau"] for r in bt], h, True), hit_decile=score(sq["d"], [r["tau"] for r in bd], h, True)) for h in HS}

    # ---- (2) volatility ratio around null-day alarms vs random times
    prep = L.Prep().fit(np.vstack([r["X"] for r in rows["train"]]), names); rr_ = np.random.default_rng(7)
    r1s = [r["r1"] for r in nr]
    configs = [(fam, "f3", thr) for fam, thr in (("gaussian_hmm", 0.999), ("student_t_hmm", 0.999), ("hsmm", 0.9999), ("bocpd", 0.999))] + [(fam, "f3", 0.99) for fam in FAMS] + [("gaussian_hmm", "base", 0.9)]
    cache = {}
    for fam, sname, thr in configs:
        sub = P.FIXED3 if sname == "f3" else []
        if (fam, sname) not in cache:
            idx = [prep.keep.index(L.RET_NAME)] + [prep.keep.index(x) for x in sub]
            mk = lambda r, idx=idx: L.build_sequence(dict(r, X=prep.transform(r["X"])[:, idx]))
            tr = [mk(r) for r in rows["train"]]; m = V.make_model(fam, K=3, lam=39, starts=1, seed=P.SEED); m.fit(L.pad(tr, len(idx)))
            qn = [mk(r) for r in nr]; cache[(fam, sname)] = (qn, V.run_filter(fam, m, qn, len(idx)))
        qn, rn = cache[(fam, sname)]; rat = []
        for q, rs, r1 in zip(qn, rn, r1s):
            for e in V.events_for(fam, rs, q, thr)[0]: rat.append(vol_ratio(r1, int(q["slots"][e["i_d"]])))
        rnd = [vol_ratio(r1, int(rr_.integers(30, 330))) for r1 in r1s for _ in range(50)]
        out["alarm_ratio"][f"{fam}|{sname}|{thr}"] = dict(alarms=qs(rat), random=qs(rnd))
    best = {}
    for var in ("raw", "des"):
        h = next((h for h in HS if out["cusum"][var][str(h)]["fa"] <= 0.05), None); best[var] = h
        for hh in ([h] if h else []) + [4]:
            rat = []
            for r in nr:
                q = variant(var, r)
                for e in detect_cusum(q["X"][:, 0], np.isfinite(q["X"][:, 0]), q["avail"], hh)[0]: rat.append(vol_ratio(r["r1"], int(r["slots"][e["i_d"]])))
            rnd = [vol_ratio(r1, int(rr_.integers(30, 330))) for r1 in r1s for _ in range(50)]
            out["alarm_ratio"][f"cusum_{var}|h={hh}"] = dict(alarms=qs(rat), random=qs(rnd))
    out["cusum_feasible_h"] = best
    (L.HERE / "results" / "cusum_results.json").write_text(json.dumps(out, indent=1))
    for var in out["cusum"]: print("CUSUM", var, " ".join(f"h{h}:{v['fa']:.2f}/{v['hit_tercile']:.2f}/{v['hit_decile']:.2f}" for h, v in out["cusum"][var].items()))
    for k, v in out["alarm_ratio"].items(): print(k, "alarms", v["alarms"], "| random", v["random"])


if __name__ == "__main__":
    main()
