#!/usr/bin/env python3
"""AMENDMENT_A38 rule 1 (primary filter check): the frozen setups on the RAW evaluation period, run on SPY from the 2026-11-11 HF Raw file and from the same-release
HF Clean file; Delta = Clean minus Raw for H1(a) and H1(b) with paired day-cluster 95% intervals; rule 2 (RAW-era criterion, secondary) and rule 3 (MDE) reported beside.
Written BEFORE the 5.12 freeze and the Section 6 fingerprint (PREFREEZE_AUDIT M4), outside the code-version closure (a0323ed24d68e896); fingerprinted (s6_fingerprint.HELPERS).

Panel (A38 1c). The study grid (the Section 3.10 canonical panel's session days and minute grid, regular hours, 390 or 210 bars) is taken from the audited Section 4
loader for the TRAIN span and the evaluation span (embargo sessions skipped, as in A36 1e). Prices come from the HF file only: a bar is observed when it is on the grid,
its source is `iex` and its OHLCV passes the Section 3.4 validity rule (finite, positive prices, volume >= 0, High >= max(Open, Close), Low <= min(Open, Close));
the SPY return into a bar is eligible when the bar and the previous minute of the session are both observed (the canonical panel's rule, checked exactly on RAW TRAIN:
`reproduce`). Features: s5_eval513.context (the 5.13 path), frozen models and preprocessing (A37), nothing fitted.
Paired design (1d). H1(a): the stable days and splice specifications of the Raw run are applied unchanged to the Clean run. H1(b): QLIKE on the decision bars common to
both runs and both models. Intervals (1e): 2,000 resamples, seed 513 (A36 5g), the same cluster draws for both runs; MDE = (1.96 + 0.84) x the bootstrap SD (3a).
Guards (5a): after the official 5.13 RAW result exists; s5_eval_loader.authorise_a38 (freeze, token, amendment list, lock, data-hash preflight, Section 6 fingerprint,
A38 adopted, the official result labelled, the HF file equal to the hash A38 records), logged; a one-shot marker per file written immediately before that file's first
evaluation-period read; per-file arrays saved after the run, so the comparison never needs a second read. Output labelled (A26), written once.
Usage: s5_a38.py reproduce                         (development only: the builder on the study's Raw file vs the canonical RAW panel, RAW TRAIN)
       s5_a38.py run FREEZE_PATH CONFIRM_TOKEN     (after the official 5.13 RAW run; refused otherwise)"""
import sys, io, json, pickle, zipfile, hashlib, datetime
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "section6"))
ERA = "RAW"; RES = HERE / "results"; OUT = RES / "a38"; RESULT_NAME = "a38_filter_check.json"; MIN_NS = 60_000_000_000; ET = "America/New_York"
HF = {"raw": dict(file=ROOT / "hfdatalibrary_raw_1min_1tickers_2026-11-11.zip", member="SPY_raw_1min.csv", sha256="b6e9da59a38deca77be6d5819c3608645dfe87ec785ca98c6eb45b2554b2feaf"),
      "clean": dict(file=ROOT / "hfdatalibrary_clean_1min_1tickers_2026-11-11.zip", member="SPY_clean_1min.csv", sha256="58f8f11245f398937cd23ab2d06ec5b170c4f7598521cfe402bc6bf2ac624c9d")}
STUDY_RAW = dict(file=ROOT / "hfdatalibrary_raw_1min_1tickers_2026-10-13.zip", member="SPY_raw_1min.csv")      # the study's own RAW source (reproduction check only)
Z = 1.96 + 0.84


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def marker(kind, res=None): return Path(res or RES) / f"a38_{kind}_RAN.marker"


# ---------- panel from an HF file on the study grid
def read_hf(path, member, first, last, chunksize=200_000):
    """Rows of the HF CSV inside [first, last] (session dates), kept chunk by chunk; any other row is discarded while streaming."""
    out = []
    with zipfile.ZipFile(path) as z, z.open(member) as f:
        for ch in pd.read_csv(f, chunksize=chunksize, dtype={"source": str}):
            dd = ch["datetime"].astype(str).str[:10]; keep = (dd >= first) & (dd <= last)
            if keep.any(): out.append(ch.loc[keep])
    df = pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["datetime", "Open", "High", "Low", "Close", "Volume", "source"])
    if len(df) and set(df["source"].astype(str).str.lower()) != {"iex"}: raise PermissionError(f"{Path(path).name}: rows with a source other than iex in {first}..{last}")
    return df


def build_panel(era, grid, hf):
    """A panel dict in the form of the audited Section 4 loader (load_development + load_ohlc) on the given grid, with prices from the HF rows."""
    t = np.asarray(grid["t"], np.int64); n = len(t)
    ts = pd.DatetimeIndex(pd.to_datetime(hf["datetime"], format="%Y-%m-%d %H:%M:%S")).tz_localize(ET, ambiguous="raise", nonexistent="raise").tz_convert("UTC").as_unit("ns").asi8.astype(np.int64)
    o, h, l, c, v = (hf[k].to_numpy(float) for k in ("Open", "High", "Low", "Close", "Volume"))
    with np.errstate(invalid="ignore"):
        ok = np.isfinite(np.c_[o, h, l, c, v]).all(axis=1) & (o > 0) & (h > 0) & (l > 0) & (c > 0) & (v >= 0) & (h >= np.maximum(o, c)) & (l <= np.minimum(o, c)) & (h >= l)
    j = np.searchsorted(t, ts); on = (j < n) & (t[np.minimum(j, n - 1)] == ts); dup = pd.Series(ts).duplicated(keep="first").to_numpy()
    use = on & ok & ~dup; jj = j[use]
    arr = {k: np.full(n, np.nan) for k in ("close", "range", "volume", "open", "high", "low")}
    arr["close"][jj] = c[use]; arr["range"][jj] = np.log(h[use] / l[use]); arr["volume"][jj] = v[use]; arr["open"][jj] = o[use]; arr["high"][jj] = h[use]; arr["low"][jj] = l[use]
    slot = np.asarray(grid["slot"], int); obs = np.isfinite(arr["close"]); valid = obs & np.r_[False, obs[:-1]] & (slot > 0)
    r = np.full(n, np.nan); ii = np.flatnonzero(valid); r[ii] = np.log(arr["close"][ii] / arr["close"][ii - 1])
    d = dict(era=era, t=t, available=t + MIN_NS, day=np.asarray(grid["day"]), slot=slot, r=r, valid=valid, first=np.asarray(grid["first"], np.int64), end=np.asarray(grid["end"], np.int64), **arr)
    counts = dict(rows=int(len(ts)), on_grid=int(on.sum()), off_grid=int((~on).sum()), invalid_ohlcv=int((on & ~ok).sum()), duplicates=int((on & dup).sum()), observed_minutes=int(obs.sum()),
                  grid_minutes=int(n), eligible_returns=int(valid.sum()))
    return d, counts


def grid_of(d): return dict(t=d["t"], day=d["day"], slot=d["slot"], first=d["first"], end=d["end"])


def reproduce(first="2022-03-07", last="2024-12-23"):
    """Development only: the builder on the study's own Raw file must reproduce the canonical RAW panel's SPY quantities exactly on RAW TRAIN (A38 1c)."""
    import s5_eval513 as S513
    can = S513._load_span(ERA, first, last); d, cnt = build_panel(ERA, grid_of(can), read_hf(STUDY_RAW["file"], STUDY_RAW["member"], first, last)); out = dict(counts=cnt, fields={})
    for k in ("close", "range", "volume", "open", "high", "low", "r"):
        a, b = can[k], d[k]; fa, fb = np.isfinite(a), np.isfinite(b)
        both = fa & fb; out["fields"][k] = dict(same_mask=bool(np.array_equal(fa, fb)), max_abs_diff=(float(np.max(np.abs(a[both] - b[both]))) if both.any() else 0.0),
                                                allclose=bool(np.allclose(a[both], b[both], rtol=1e-10, atol=1e-12)))
    out["valid_equal"] = bool(np.array_equal(can["valid"], d["valid"])); out["n_sessions"] = int(len(can["first"]))
    out["passed"] = out["valid_equal"] and all(v["same_mask"] and v["allclose"] for v in out["fields"].values())
    return out


# ---------- statistics (A38 1e, 3a)
def _w(n, nboot, seed): return np.random.default_rng(seed).multinomial(n, np.full(n, 1.0 / n), size=nboot).astype(float)


def boot_mean_diff(y1, y0, clusters, nboot=2000, seed=513):
    """mean(y1) - mean(y0) over paired rows; percentile interval and SD from cluster resampling (A36 5g settings)."""
    y1, y0 = np.asarray(y1, float), np.asarray(y0, float)
    if len(y1) == 0: return dict(effect=None, ci95=None, sd=None, mde=None, n=0, n_clusters=0)
    u, inv = np.unique(np.asarray(clusters), return_inverse=True); n = np.bincount(inv, minlength=len(u)).astype(float); s1, s0 = np.bincount(inv, y1, len(u)), np.bincount(inv, y0, len(u))
    W = _w(len(u), nboot, seed); bs = (W @ s1 - W @ s0) / (W @ n); lo, hi = np.percentile(bs, [2.5, 97.5]); sd = float(np.std(bs, ddof=1))
    return dict(effect=float((s1.sum() - s0.sum()) / n.sum()), ci95=[float(lo), float(hi)], sd=sd, mde=Z * sd, n=int(n.sum()), n_clusters=int(len(u)))


def _pa(c, h, wn, wb):
    import s5_a6 as A
    return A.pauc(list(zip(((wn @ c) / wn.sum()).tolist(), ((wb @ h) / wb.sum()).tolist())))


def boot_pauc(mats, nboot=2000, seed=513):
    """mats: list of (sign, feature matrices, baseline matrices) on the SAME splices (days). Statistic = sum of sign x [pAUC(feature) - pAUC(baseline)]; stable days
    resampled jointly (A36 5g); a resample without a null or a break splice is left out (counted)."""
    dn, db_ = mats[0][1][1], mats[0][1][3]; days = np.unique(np.r_[dn, db_]); idn, idb = np.searchsorted(days, dn), np.searchsorted(days, db_)
    stat = lambda wn, wb: sum(s * (_pa(mf[0], mf[2], wn, wb) - _pa(mb[0], mb[2], wn, wb)) for s, mf, mb in mats)
    est = stat(np.ones(len(dn)), np.ones(len(db_))); bs = []
    for w in _w(len(days), nboot, seed):
        wn, wb = w[idn], w[idb]
        if wn.sum() > 0 and wb.sum() > 0: bs.append(stat(wn, wb))
    lo, hi = np.percentile(bs, [2.5, 97.5]) if bs else (np.nan, np.nan); sd = float(np.std(bs, ddof=1)) if len(bs) > 1 else None
    return dict(effect=float(est), ci95=[float(lo), float(hi)], sd=sd, mde=(Z * sd if sd is not None else None), n_null=int(len(dn)), n_break=int(len(db_)), n_days=int(len(days)), n_valid_resamples=len(bs))


def h1b_rows(run):
    """{family: (keys, baseline loss, feature loss)} on the run's common bars (s5_eval.align)."""
    import s5_eval as V
    out = {}
    for fam, x in run["families"].items():
        xb, xf, common = V.align(np.asarray(x["lb"], float), np.asarray(x["kb"]), np.asarray(x["lf"], float), np.asarray(x["kf"])); ok = np.isfinite(xb) & np.isfinite(xf)
        out[fam] = (np.asarray(common)[ok], xb[ok], xf[ok])
    return out


def compare(raw, clean, nboot=2000, seed=513):
    """A38 1d-1f per family: each run's effects and the paired Delta (Clean minus Raw) with intervals and MDE."""
    rb, cb = h1b_rows(raw), h1b_rows(clean); fams = {}
    for fam in raw["families"]:
        kr, br, fr = rb[fam]; kc, bc, fc = cb[fam]; com, ir, ic = np.intersect1d(kr, kc, return_indices=True)
        cl = com // 1000; e_r = boot_mean_diff(br[ir], fr[ir], cl, nboot, seed); e_c = boot_mean_diff(bc[ic], fc[ic], cl, nboot, seed)
        d_b = boot_mean_diff(bc[ic] - fc[ic], br[ir] - fr[ir], cl, nboot, seed)
        r = dict(H1b=dict(raw=e_r, clean=e_c, delta=d_b, n_common_bars=int(len(com)), n_bars_raw_only=int(len(kr) - len(com)), n_bars_clean_only=int(len(kc) - len(com))))
        ma, mc = raw["families"][fam].get("h1a"), clean["families"][fam].get("h1a"); dr = clean.get("splice_drop")
        if ma and mc:
            mk = (lambda m: subset_h1a(m, dr["keep_null"], dr["keep_brk"])) if dr else (lambda m: m)      # A38 N2: the Raw run on the kept specifications only
            ka = dict(feature=mk(ma["feature"]), baseline=mk(ma["baseline"]))
            r["H1a"] = dict(raw=boot_pauc([(1, ka["feature"], ka["baseline"])], nboot, seed), clean=boot_pauc([(1, mc["feature"], mc["baseline"])], nboot, seed),
                            delta=boot_pauc([(1, mc["feature"], mc["baseline"]), (-1, ka["feature"], ka["baseline"])], nboot, seed),
                            raw_all_specs_reference=(boot_pauc([(1, ma["feature"], ma["baseline"])], nboot, seed) if dr else None))
        else: r["H1a"] = dict(delta=None, note=raw["families"][fam].get("h1a_note") or clean["families"][fam].get("h1a_note") or "not evaluable")
        dl = [x["delta"] for x in (r["H1a"], r["H1b"]) if x.get("delta")]
        sens = any(x["ci95"] is not None and np.isfinite(x["ci95"][0]) and (x["ci95"][0] > 0 or x["ci95"][1] < 0) for x in dl)
        r["reading"] = ("filter-sensitive on IEX data (a 95% interval of Delta excludes 0)" if sens else "no detectable filter effect (both intervals include 0; see the MDE)") if len(dl) == 2 else "not evaluable on both components"
        fams[fam] = r
    return fams


def reproducibility(official, raw, nboot=2000, seed=513):
    """A38 1g: the Raw-file run on its own (its common bars, its splices) beside the official 5.13 RAW result (study Raw download of 2026-10-13); the official result stays."""
    rb = h1b_rows(raw); out = {}
    for fam, x in official["families"].items():
        k, b, f = rb[fam]; m = raw["families"][fam].get("h1a"); e_b = boot_mean_diff(b, f, k // 1000, nboot, seed); e_a = boot_pauc([(1, m["feature"], m["baseline"])], nboot, seed) if m else None
        ob, oa = (x.get("H1b") or {}).get("effect"), (x.get("H1a") or {}).get("effect")
        out[fam] = dict(official=dict(H1a=oa, H1b=ob), raw_file_2026_11_11=dict(H1a=(e_a or {}).get("effect"), H1b=e_b["effect"]),
                        difference=dict(H1a=(e_a["effect"] - oa if e_a and oa is not None else None), H1b=(e_b["effect"] - ob if ob is not None and e_b["effect"] is not None else None)))
    return out


def secondary(official, fz):
    """A38 rule 2 (and 3 beside it) from the official 5.13 RAW result: robust only if both RAW-era effects are positive with intervals excluding 0, for families the
    development run rejected (H1 verdicts of the freeze); MDE approximated from the percentile interval (SD = width / 3.92), as the official file stores no SD."""
    rej = {f: bool((fz.get("h1_verdicts") or {}).get(f, {}).get("reject")) for f in official["families"]}; out = {}
    for fam, x in official["families"].items():
        def one(k):
            e = x.get(k) or {}; ci = e.get("ci95"); sd = ((ci[1] - ci[0]) / 3.92) if ci and all(np.isfinite(ci)) else None
            return dict(effect=e.get("effect"), ci95=ci, mde_approx=(Z * sd if sd is not None else None), skipped=e.get("skipped"))
        a, b = one("H1a"), one("H1b"); both = all(v["effect"] is not None and v["effect"] > 0 and v["ci95"] and v["ci95"][0] > 0 for v in (a, b))
        lab = None if fam == "bocpd" or not rej.get(fam) else ("robust to the LEGACY Clean filter" if both else "possibly filter-dependent (LEGACY-era results)")
        out[fam] = dict(H1a=a, H1b=b, development_verdict_reject=rej.get(fam), label=lab)
    return out


# ---------- A38 note N1-N4 (2026-11-12): Raw splices that cannot be built on the Clean panel
SPEC_FIELDS = dict(plain=("kind", "cell", "iA", "iB", "g"), regime=("kind", "cell", "iA", "iB", "g", "f", "dur"))


def check_raw_specs(raw_specs):
    """N4, ahead of the Clean marker: the saved Raw run holds its splice specifications, each with the fields the screen and the builder need."""
    if not isinstance(raw_specs, dict) or "specs" not in raw_specs or "n_stable" not in raw_specs: raise RuntimeError("A38 N4: the saved Raw run holds no splice specifications")
    for i, s in enumerate(raw_specs["specs"]):
        need = SPEC_FIELDS.get(s.get("kind"))
        if need is None or any(k not in s for k in need): raise RuntimeError(f"A38 N4: Raw splice specification {i} is incomplete: {s}")
    return len(raw_specs["specs"])


def spec_end(s): return (int(s["g"]) + int(s["dur"])) if s.get("kind") == "regime" and s.get("dur") is not None else None


def screen_specs(d, specs):
    """N1 on a panel: True where s5_d2.finite_ok holds (the rule that drew the specifications on the Raw panel)."""
    import s5_d2 as D2
    return [bool(D2.finite_ok(d, int(s["iA"]), int(s["iB"]), int(s["g"]), spec_end(s))) for s in specs]


def build_kept(specs, ok, work):
    """N1-N3: build every screened specification inside error handling; returns (kept specs, rows, keep mask, dropped records). Never raises for a splice."""
    kept, rows, keep, dropped = [], [], [], []
    for i, (s, k) in enumerate(zip(specs, ok)):
        if k:
            try: rows.append(work(s)); kept.append(s); keep.append(True); continue
            except Exception as ex: dropped.append(dict(index=i, cell=str(s.get("cell")), why=f"build error: {type(ex).__name__}: {ex}"[:300]))
        else: dropped.append(dict(index=i, cell=str(s.get("cell")), why="not buildable on the Clean panel (s5_d2.finite_ok)"))
        keep.append(False)
    return kept, rows, keep, dropped


def drop_summary(specs, keep, dropped):
    """N3: counts and shares, split into null and break splices."""
    isn = [s.get("cell") == "null" for s in specs]; n = len(specs); nd = n - sum(keep)
    nn = sum(isn); nb = n - nn; dn = sum(1 for s, k in zip(isn, keep) if s and not k); db_ = nd - dn
    return dict(n_specs=n, n_dropped=nd, share_dropped=(nd / n if n else None), null=dict(n=nn, dropped=dn, share=(dn / nn if nn else None)),
                brk=dict(n=nb, dropped=db_, share=(db_ / nb if nb else None)), dropped=dropped)


def subset_h1a(m, keep_null, keep_brk):
    """The Raw run's H1(a) matrices (null counts, null days, break hits, break days) restricted to the kept specifications (N2)."""
    kn, kb = np.asarray(keep_null, bool), np.asarray(keep_brk, bool)
    return (np.asarray(m[0])[kn], np.asarray(m[1])[kn], np.asarray(m[2])[kb], np.asarray(m[3])[kb])


# ---------- one file's run (the guarded read happens here)
def run_file(kind, freeze, token, bundles, raw_specs=None, res=None):
    import s5_eval_loader as EL, s5_eval513 as S513, s5_d2 as D2
    res = Path(res or RES); spec = HF[kind]
    if sha(spec["file"]) != spec["sha256"]: raise PermissionError(f"{Path(spec['file']).name} differs from the hash AMENDMENT_A38 records")
    if kind == "clean": check_raw_specs(raw_specs)      # A38 N4: ahead of the Clean authorisation and marker
    EL.authorise_a38(kind, freeze, token, what=f"A38 1a: SPY from {Path(spec['file']).name}; study grid of the RAW evaluation span")      # guard + access log (no read yet)
    mk = marker(kind, res)
    if mk.exists(): raise SystemExit(f"A38 {kind}: the one-shot marker exists without saved arrays; no second run (A38 5a); the user decides")
    mk.write_text(f"{datetime.datetime.now(datetime.timezone.utc).isoformat()} {sha(freeze)}\n", encoding="ascii")      # immediately before the first evaluation read
    (f, l), (ef, el) = EL.DEV[ERA], EL.EVAL[ERA]; g_tr = grid_of(S513._load_span(ERA, f, l)); g_ev = grid_of(S513._load_span(ERA, ef, el))
    n_tr = len(g_tr["first"]); n0 = len(g_tr["t"]); grid = dict(t=np.r_[g_tr["t"], g_ev["t"]], day=np.r_[g_tr["day"], g_ev["day"]], slot=np.r_[g_tr["slot"], g_ev["slot"]],
                                                              first=np.r_[g_tr["first"], g_ev["first"] + n0], end=np.r_[g_tr["end"], g_ev["end"] + n0])
    d, cnt = build_panel(ERA, grid, read_hf(spec["file"], spec["member"], f, el)); S513.check_partitions(ERA, [str(d["day"][i]) for i in d["first"]], n_tr)
    ok = screen_specs(d, raw_specs["specs"]) if raw_specs is not None else None      # A38 N1/N4: the screen runs first, on the Clean panel, before any model
    est = S513.build_eval_state(ERA, d, n_tr, bundles); db = est["full"]; drop = None
    if raw_specs is not None:      # A38 1d with note N1-N3: the Raw run's splice specifications; those not buildable on the Clean panel are dropped (from both runs, in compare)
        c = db.c; D2._W.update(d=c["d"], cols=c["cols"], bases=db._shared["bases"], dv=c["dv"])
        kept, rows, keep, dropped = build_kept(raw_specs["specs"], ok, D2._work); drop = drop_summary(raw_specs["specs"], keep, dropped)
        drop["keep_null"] = [k for s, k in zip(raw_specs["specs"], keep) if s.get("cell") == "null"]; drop["keep_brk"] = [k for s, k in zip(raw_specs["specs"], keep) if s.get("cell") != "null"]
        db._splice = dict(n_stable=raw_specs["n_stable"], specs=kept, rows=rows, why=None)
    sp = db._splices(); out = dict(kind=kind, file=Path(spec["file"]).name, sha256=spec["sha256"], panel_counts=cnt, n_train=n_tr, n_stable=sp["n_stable"], families={}, splice_drop=drop)
    has_both = bool(sp["specs"]) and any(s.get("cell") == "null" for s in sp["specs"]) and any(s.get("cell") != "null" for s in sp["specs"])
    for fam, b in bundles.items():
        mf, mb, feats = b["feature"], b["baseline"], tuple(b["features"]); lf, kf = db.qlike_on(fam, mf, feats, "test"); lb, kb = db.qlike_on(fam, mb, (), "test")
        x = dict(lf=np.asarray(lf, float), kf=np.asarray(kf), lb=np.asarray(lb, float), kb=np.asarray(kb))
        if raw_specs is not None and not has_both: x["h1a_note"] = "A38 N3: no null or no break splice kept on the Clean panel"
        elif sp["specs"] and sp["n_stable"] >= S513.MIN_STABLE: x["h1a"] = dict(feature=db.h1a_matrices(fam, mf, feats), baseline=db.h1a_matrices(fam, mb, ()))
        else: x["h1a_note"] = f"{sp['n_stable']} stable days" if sp["n_stable"] < S513.MIN_STABLE else (sp["why"] or "no splice specs")
        out["families"][fam] = x
    out["specs"] = dict(n_stable=sp["n_stable"], specs=sp["specs"]) if raw_specs is None else None
    p = OUT_DIR(res) / f"{kind}.pkl"; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(pickle.dumps(out, protocol=4)); p.with_suffix(".sha256").write_text(f"{sha(p)}  {p.name}\n", encoding="ascii")
    return out


def OUT_DIR(res=None): return Path(res or RES) / "a38"


def load_saved(kind, res=None):
    p = OUT_DIR(res) / f"{kind}.pkl"; side = p.with_suffix(".sha256")
    if not p.exists(): return None
    if not side.exists() or side.read_text().split()[0] != sha(p): raise PermissionError(f"{p.name} differs from its sidecar")
    return pickle.loads(p.read_bytes())


def run(freeze, token, res=None, nboot=2000, seed=513):
    """The A38 rule 1 runs (Raw, then Clean) and the report. Each file is read once (its marker); saved arrays are reused, never re-read."""
    import s5_freeze as FZ, s5_eval513 as S513, s5_eval_label as EV, s6_run as R
    res = Path(res or RES); out_p = res / RESULT_NAME
    if out_p.exists(): print("result exists; written once"); return 0
    fz = FZ.verify_freeze(freeze)
    if token != FZ.sha(freeze): raise PermissionError("confirm_token must be the sha256 of the freeze file")
    off = res / f"{FZ.EVAL_PREFIX}{ERA}.json"
    if not off.exists(): raise PermissionError("A38 5a: the official 5.13 RAW result must exist first")
    EV.verify_labelled(res); bundles = S513.load_frozen(ERA, fz)["bundles"]; runs = {}
    for kind in ("raw", "clean"):
        runs[kind] = load_saved(kind, res) or run_file(kind, freeze, token, bundles, raw_specs=(runs["raw"]["specs"] if kind == "clean" else None), res=res)
    official = json.loads(off.read_text(encoding="utf-8"))
    rep = dict(label="AMENDMENT_A38 filter checks of H1 on the RAW evaluation period", period="evaluation", a26_label=EV.LABEL, confirmatory=False,
               primary_rule1=dict(by_family=compare(runs["raw"], runs["clean"], nboot, seed), panel_counts={k: v["panel_counts"] for k, v in runs.items()}, n_stable_days=runs["raw"]["n_stable"],
                                  splice_drop_note_N3={k: v for k, v in (runs["clean"].get("splice_drop") or {}).items() if k not in ("keep_null", "keep_brk")},
                                  note="HF's documented Clean filter on IEX data: the closest available proxy for the processing of the LEGACY rows, not the same thing (A38 background, 4b)"),
               secondary_rule2=secondary(official, fz),
               reproducibility_rule1g=reproducibility(official, runs["raw"], nboot, seed),
               reading="A38 rule 4: 'possibly filter-dependent' is not a finding of dependence and may reflect limited power in the RAW evaluation period (see each MDE); 'robust' and "
                       "'no detectable filter effect' do not show that the processing of the LEGACY rows had no effect.",
               freeze_sha256=sha(freeze), generated=datetime.datetime.now(datetime.timezone.utc).isoformat())
    R.write_once(out_p, rep); print(f"written {out_p}"); return 0


def main():
    a = sys.argv[1:]
    if a[:1] == ["reproduce"]: r = reproduce(); print(json.dumps(r, indent=1)); return 0 if r["passed"] else 1
    if len(a) >= 3 and a[0] == "run": return run(Path(a[1]), a[2])
    print(__doc__); return 3


if __name__ == "__main__": sys.exit(main())
