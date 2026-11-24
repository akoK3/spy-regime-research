#!/usr/bin/env python3
# Provenance: written separately from the research code, in the MarketLens repository (github.com/akoK3/MarketLens,
# tools/acceptance_repro.py, last changed in commit 28a6b0d; copied from MarketLens commit bdd6de1). It reruns the frozen RAW
# Gaussian HMM through MarketLens's own loader, bar builder and live code path and compares every run with
# section5/results/evaluation_RAW.json. Its dependencies are copied unchanged into tools/regime/ (MarketLens regime/
# __init__, frozen_loader, core, live, panel, and the hash-locked vendored copies of research files in regime/frozen/,
# byte-identical to the files of this repository). Only this comment was added.
# Run from the repository root:  python tools/acceptance_repro.py .   (needs the RAW panel and SPY file of DATA.md;
# writes acceptance/acceptance_report.json and its .sha256 at the repository root).
"""Exact-reproduction acceptance test of the vendored frozen detector against the research evaluation record.

Target: section5/results/evaluation_RAW.json (vendored, hash-pinned): every Gaussian HMM run on the 445 RAW evaluation sessions
(2025-01-02..2026-10-12): kind (confirmed / fizzle / open_at_close), S_min (T_d), T0_min (T_c), end_min, old and new state.

Input data (read-only, hash-checked against REPRODUCIBILITY_FACTS.md): the RAW canonical panel and the SPY IEX bar file of the
research repository, TRAIN span 2022-03-07..2024-12-23 followed by the evaluation span (the 5 embargo sessions are not read),
exactly as section5/s5_eval513.panel joins them. NOTE: this read happens outside the research evaluation guard
(s5_eval_loader.authorise), so it is not in the research access log; it is recorded in this script's report instead.

  A  research loader (vendored load_development + load_ohlc) -> regime.core            must reproduce every run exactly
  B  MarketLens bar builder (regime.panel) from the raw bar rows -> regime.core         panel arrays equal to A (r: same NaN mask and
     |diff| <= 1e-15, since the panel stores r as CSV text); every run exactly
  C  live code path (regime.live.evaluate_at), stepped grid slot by grid slot with only the 20 prior sessions as history,
     on every evaluation day with a confirmed alarm plus 15 seeded random days            alarms as emitted live == the record
Exit 0 only if A, B and C all pass. Writes acceptance/acceptance_report.json (+ .sha256).
Usage: python tools/acceptance_repro.py [RESEARCH_ROOT] [--quick]"""
import sys, json, time, hashlib, datetime
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(HERE))
from regime import frozen_loader as FL, core, live, panel as PN  # noqa: E402

PANEL = "section3_10_alignment_results/canonical_panel_RAW_1m.csv.gz"
ETF = "section3_4_etf_results/etf_observed_SPY_RAW.csv.gz"
PINNED = {PANEL: "f1b1c498dc76c7ef11e53a31fec655abacaf6458d8f3b9dd1827f9dd8ec91184", ETF: "6c37b2798d3cc5740d71de94c34343d315fa274b95e50a5a7df081c1b7a5928d"}
TRAIN = ("2022-03-07", "2024-12-23"); EVAL = ("2025-01-02", "2026-10-12")
KEYS = ("day", "kind", "S_min", "T0_min", "end_min", "old", "new")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def concat(a, b):
    """section5/s5_eval513.concat."""
    n = len(a["t"]); out = {k: np.concatenate([v, b[k]]) for k, v in a.items() if isinstance(v, np.ndarray) and k not in ("first", "end") and v.shape[:1] == (n,)}
    out["first"] = np.r_[a["first"], b["first"] + n].astype(np.int64); out["end"] = np.r_[a["end"], b["end"] + n].astype(np.int64); return out


def research_panel(root):
    m = FL.modules(); C, S3 = m["candidates"], m["step3"]; parts = []
    for f, l in (TRAIN, EVAL):
        spec = dict(first_session=f, last_session=l, panel_file=str(root / PANEL), etf_file=str(root / ETF))
        d = C.load_development("RAW", spec); d.update(S3.load_ohlc(spec, d)); parts.append(d)
    return concat(*parts), len(parts[0]["first"])


def bars_from_etf(root):
    import pandas as pd
    e = pd.read_csv(root / ETF, usecols=["utc_minute_start", "session_date_ny", "Open", "High", "Low", "Close", "Volume"])
    e = e[e.session_date_ny.between(*TRAIN) | e.session_date_ny.between(*EVAL)]
    t = pd.DatetimeIndex(pd.to_datetime(e.utc_minute_start, utc=True)).as_unit("ns").asi8
    return dict(t=t, o=e.Open.to_numpy(float), h=e.High.to_numpy(float), l=e.Low.to_numpy(float), c=e.Close.to_numpy(float), v=e.Volume.to_numpy(float))


def sessions_of(d):
    return [dict(day=str(d["day"][a]), open_ns=int(d["t"][a]), close_ns=int(d["t"][a] + (b - a) * PN.MIN)) for a, b in zip(d["first"], d["end"])]


def target():
    ev = json.loads((FL.SRC / "section5/results/evaluation_RAW.json").read_text(encoding="utf-8"))
    rows = [dict(day=x["day"], kind=x["kind"], S_min=x["S_min"], T0_min=x["T0_min"], end_min=x["end_min"], old=x["old_state"], new=x["new_state"])
            for x in ev["breaks"] if x["family"] == "gaussian_hmm"]
    return ev, rows


def as_rows(res):
    return [dict(day=r["day"], **{k: x[k] for k in KEYS if k != "day"}) for r in res for x in r["runs"]]


def compare(mine, ref):
    a = [tuple(x[k] for k in KEYS) for x in mine]; b = [tuple(x[k] for k in KEYS) for x in ref]
    sa, sb = set(a), set(b)
    return dict(n_mine=len(a), n_ref=len(b), equal=a == b, only_mine=sorted(sa - sb)[:10], only_ref=sorted(sb - sa)[:10])


def nan_equal(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    return bool(x.shape == y.shape and np.array_equal(np.isnan(x), np.isnan(y)) and np.array_equal(x[~np.isnan(x)], y[~np.isnan(y)]))


def main(root, quick=False):
    t0 = time.time(); root = Path(root).resolve(); rep = dict(kind="marketlens_acceptance_exact_reproduction", started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
    rep["verification"] = FL.verify(); bundle, _ = FL.load_bundle()
    rep["research_files_read"] = {}
    for rel, h in PINNED.items():
        got = sha(root / rel); rep["research_files_read"][rel] = dict(sha256=got, pinned=h, ok=got == h)
        if got != h: raise SystemExit(f"{rel}: SHA-256 differs from REPRODUCIBILITY_FACTS.md")
    rep["research_files_read"]["note"] = "read-only, outside the research evaluation guard (not in the research access log)"
    ev, ref = target(); rep["target"] = dict(file="section5/results/evaluation_RAW.json", sha256=FL.EVALUATION_RAW_SHA256, n_runs=len(ref),
                                            by_kind={k: sum(x["kind"] == k for x in ref) for k in ("confirmed", "fizzle", "open_at_close")}, n_sessions=len(ev["sessions"]))
    print(f"target: {rep['target']}", flush=True)

    # ---- A
    dA, n_tr = research_panel(root); evi = list(range(n_tr, len(dA["first"])))
    daysA = [str(dA["day"][dA["first"][i]]) for i in evi]
    resA = core.run_sessions(dA, evi, bundle, batch=True)
    cA = compare(as_rows(resA), ref); cA["sessions_equal"] = daysA == ev["sessions"]
    n_conf = sum(len(r["events"]) for r in resA)
    cA["alarms_per_session"] = dict(mine=n_conf / len(evi), research=ev["families"]["gaussian_hmm"]["alarms_per_session"]["feature"])
    cA["pass"] = bool(cA["equal"] and cA["sessions_equal"] and abs(cA["alarms_per_session"]["mine"] - cA["alarms_per_session"]["research"]) < 1e-12)
    rep["A_research_loader"] = cA; print("A:", {k: v for k, v in cA.items() if k not in ("only_mine", "only_ref")}, f"{time.time()-t0:.0f}s", flush=True)

    # ---- B
    bars = bars_from_etf(root); sess = sessions_of(dA); dB = PN.build_panel(sess, bars)
    arrays = {k: nan_equal(dA[k], dB[k]) for k in ("close", "open", "high", "low", "volume", "range")}
    rd = np.abs(dA["r"] - dB["r"])[np.isfinite(dA["r"])]
    arrays["r_nan_mask_equal"] = bool(np.array_equal(np.isnan(dA["r"]), np.isnan(dB["r"])))
    arrays["r_within_1e-15"] = bool(rd.max() <= 1e-15)        # the panel stores r as CSV text: bit-identity is not reachable (max |diff| reported)
    arrays.update(t=bool(np.array_equal(dA["t"], dB["t"])), available=bool(np.array_equal(dA["available"], dB["available"])), slot=bool(np.array_equal(dA["slot"], dB["slot"])),
                  valid=bool(np.array_equal(dA["valid"], dB["valid"])), first=bool(np.array_equal(dA["first"], dB["first"])), day=bool(np.array_equal(dA["day"], dB["day"])))
    resB = core.run_sessions(dB, evi, bundle, batch=True); cB = compare(as_rows(resB), ref); cB["panel_arrays_equal"] = arrays; cB["r_max_abs_diff"] = float(rd.max()); cB["r_bit_identical_share"] = float(np.mean(rd == 0))
    cB["pass"] = bool(cB["equal"] and all(arrays.values()))
    rep["B_marketlens_bar_builder"] = cB; print("B:", {k: v for k, v in cB.items() if k not in ("only_mine", "only_ref")}, f"{time.time()-t0:.0f}s", flush=True)

    # ---- C: live path, slot by slot, 20 prior sessions only
    conf_days = sorted({x["day"] for x in ref if x["kind"] == "confirmed"})
    rng = np.random.default_rng(20261114); others = sorted(set(ev["sessions"]) - set(conf_days))
    days = conf_days + sorted(rng.choice(others, size=15, replace=False).tolist())
    if quick: days = days[:5]
    idx = {s["day"]: k for k, s in enumerate(sess)}; mismatches = []; n_steps = 0; emitted_total = 0; ref_conf = {}
    for x in ref:
        if x["kind"] == "confirmed": ref_conf.setdefault(x["day"], []).append((x["S_min"], x["T0_min"]))
    for day in days:
        k = idx[day]; hist = sess[k - core.BASELINE_SESSIONS:k + 1]; s = hist[-1]
        lo, hi = hist[0]["open_ns"], s["close_ns"]; sel = (bars["t"] >= lo) & (bars["t"] < hi); b = {kk: v[sel] for kk, v in bars.items()}
        emitted = []
        for g in live.due_slots(s["open_ns"], s["close_ns"], s["close_ns"] + PN.MIN):
            upto = s["open_ns"] + (g + 1) * PN.MIN; res, nprior = live.evaluate_at(hist, b, upto, bundle); n_steps += 1
            assert nprior == core.BASELINE_SESSIONS
            if res is None or not len(res["slots"]) or int(res["slots"][-1]) != g: continue
            for e in res["events"]:
                if e["i_c"] == len(res["slots"]) - 1: emitted.append((e["S_min"], e["T0_min"]))     # emitted when it confirms, as the engine does
        emitted_total += len(emitted)
        if emitted != ref_conf.get(day, []): mismatches.append(dict(day=day, live=emitted, record=ref_conf.get(day, [])))
    cC = dict(days=len(days), confirmed_alarm_days=len([d for d in days if d in conf_days]), grid_steps=n_steps, alarms_emitted=emitted_total,
              alarms_in_record_for_these_days=sum(len(ref_conf.get(d, [])) for d in days), mismatches=mismatches, pass_=not mismatches and not quick)
    cC["pass"] = cC.pop("pass_")
    rep["C_live_path_stepwise"] = cC; print("C:", cC, f"{time.time()-t0:.0f}s", flush=True)

    rep["pass"] = bool(cA["pass"] and cB["pass"] and cC["pass"]); rep["seconds"] = round(time.time() - t0, 1)
    rep["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    out = HERE / "acceptance"; out.mkdir(exist_ok=True); p = out / "acceptance_report.json"
    p.write_text(json.dumps(rep, indent=1, default=str) + "\n", encoding="utf-8"); (out / "acceptance_report.sha256").write_text(f"{sha(p)}  {p.name}\n")
    print("PASS" if rep["pass"] else "FAIL", p)
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sys.exit(main(args[0] if args else Path.home() / "Downloads", quick="--quick" in sys.argv))
