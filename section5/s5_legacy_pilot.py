#!/usr/bin/env python3
"""Machinery pilot on the smallest LEGACY fold (fold 29: 189 train / 63 val / 116 test sessions), same checks as the A7 RAW pilot (s5_a7.py) plus LEGACY-specific checks
(missing data, causal availability, fold isolation, checkpoint recovery). Modes: `build` (one-time LEGACY feature build, timed alone) and `run` (everything else; resumable).
Every unit of work is checkpointed (section5/cache/legacy_ckpt); the elapsed seconds of each unit are stored with it, so timings survive a kill. TRAIN sessions only;
no evaluation-period data, no selection, no protocol change."""
import sys, os, json, time, ctypes, threading
from ctypes import wintypes
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_eval as V, s5_fast as F, s5_pilot as P, s5_events as E, s5_d2 as D2, s5_d2_stable as S, s5_a6 as A, s5_a7 as B, s5_sweep as W

ERA, FOLD = "LEGACY", 29
WORKERS = int(os.environ.get("S5_WORKERS", "3")); CHUNK = 100
RES = L.HERE / "results"; CK = L.Checkpoint(L.CACHE / "legacy_ckpt"); MEMLOG = RES / "legacy_mem.json"
_G = {}


# ---------------- memory (Windows) ----------------
class _PMC(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]


class _MS(ctypes.Structure):
    _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD), ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def peak_mb(pid=None):
    k = ctypes.WinDLL("kernel32", use_last_error=True); k.OpenProcess.restype = wintypes.HANDLE
    h = k.GetCurrentProcess() if pid is None else k.OpenProcess(0x1010, False, pid)
    if not h: return None
    c = _PMC(); c.cb = ctypes.sizeof(c); ok = ctypes.WinDLL("psapi").GetProcessMemoryInfo(wintypes.HANDLE(h), ctypes.byref(c), c.cb)
    if pid is not None: k.CloseHandle(wintypes.HANDLE(h))
    return round(c.PeakWorkingSetSize / 2 ** 20, 1) if ok else None


def free_mb():
    m = _MS(); m.dwLength = ctypes.sizeof(m); ctypes.WinDLL("kernel32").GlobalMemoryStatusEx(ctypes.byref(m)); return m.ullAvailPhys / 2 ** 20


class Mem:
    """Samples the system's free RAM and the peak working set of this process and its pool workers every 2 s; writes legacy_mem.json (so a killed run keeps its numbers)."""
    def __init__(self, tag): self.tag = tag; self.min_free = free_mb(); self.pids = []; self.child_peak = {}; self.stop = False; self.t = threading.Thread(target=self.loop, daemon=True)
    def loop(self):
        while not self.stop:
            self.min_free = min(self.min_free, free_mb())
            for p in list(self.pids):
                v = peak_mb(p)
                if v: self.child_peak[p] = max(v, self.child_peak.get(p, 0))
            self.dump(); time.sleep(2)
    def dump(self):
        allm = json.loads(MEMLOG.read_text()) if MEMLOG.exists() else {}
        allm[self.tag] = dict(parent_peak_mb=peak_mb(), worker_peak_mb=sorted(self.child_peak.values()), min_system_free_mb=round(self.min_free), updated=time.strftime("%H:%M:%S"))
        MEMLOG.write_text(json.dumps(allm, indent=1))
    def __enter__(self): self.t.start(); return self
    def __exit__(self, *a): self.stop = True; time.sleep(0.1); self.dump()


def unit(key, fn):
    """Checkpointed unit; returns (value, seconds) where seconds is the original compute time."""
    def go():
        t0 = time.perf_counter(); v = fn(); return v, time.perf_counter() - t0
    return CK.run(key, go)


# ---------------- worker side ----------------
def _init(cols):
    d = L.load_era(ERA, cols + ["lee_mykland_approx60"]); _G.update(d=d, cols=cols, bases=F.load_bases(d, ERA, cols)); D2._W.update(d=d, cols=cols, bases=_G["bases"])


def _work_chunk(args):
    ci, specs = args
    return ci, [D2._work(s) for s in specs]


# ---------------- build mode ----------------
def build():
    primary, _, _ = L.pools(); cols = primary
    t0 = time.perf_counter()
    with Mem("build"):
        d = L.load_era(ERA, cols + ["lee_mykland_approx60"]); t1 = time.perf_counter()
        F.load_bases(d, ERA, cols); t2 = time.perf_counter()
        _ = F.ret5_matrix(d, cols); t3 = time.perf_counter()
        _ = S.des_variance(d); t4 = time.perf_counter()
        res = dict(rows=int(len(d["t"])), sessions=int(len(d["first"])), seconds_load_panel_and_19_plus_LM_features=round(t1 - t0, 1), seconds_bases_for_sadj_features=round(t2 - t1, 1),
                   seconds_ret5_matrix=round(t3 - t2, 1), seconds_des_variance=round(t4 - t3, 1), seconds_total=round(t4 - t0, 1), peak_mb=peak_mb(),
                   cache_files={f.name: round(f.stat().st_size / 2 ** 20, 1) for f in L.CACHE.glob(f"{ERA}_*.npz")})
    (RES / "legacy_build.json").write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


# ---------------- run mode ----------------
def run():
    import multiprocessing as mp
    T0 = time.time(); log = lambda m: print(f"[{(time.time()-T0)/60:5.1f} min] {m}", flush=True); tag = f"run_{int(time.time())}"
    out = dict(checks={}, calibration={}, scoring={}, era=ERA, fold=FOLD, stage_seconds={})
    primary, sens, sens_all = L.pools(); cols = primary; names = [L.RET_NAME] + cols; ST = out["stage_seconds"]
    with Mem(tag) as mem:
        t0 = time.perf_counter(); d = L.load_era(ERA, cols + ["lee_mykland_approx60"]); seg = L.fold_segments(d, ERA, FOLD); dv = S.des_variance(d)
        native = [L.session_grid(d, i, cols) for i in range(len(d["first"]))]; Mx = np.full((len(native), 78), np.nan)
        for i, r in enumerate(native): Mx[i, :len(r["X"])] = r["X"][:, 0]
        ST["load_from_cache_and_grid"] = round(time.perf_counter() - t0, 1)
        out["segments"] = {k: len(seg[k]) for k in ("train", "val", "test")}; out["fold_row"] = seg["row"]
        # ---- exclusions
        ex = {}
        def chk(name, fn):
            try: fn(); ex[name] = "PASS"
            except AssertionError as e: ex[name] = f"FAIL: {e}"
        chk("primary pool = 19", lambda: (L.assert_pool(primary, "primary"), len(primary) == 19 or (_ for _ in ()).throw(AssertionError(len(primary)))))
        chk("sensitivity pool = 80", lambda: (L.assert_pool(sens, "sensitivity"), (len(sens) == 80 and len(sens_all) == 83) or (_ for _ in ()).throw(AssertionError((len(sens), len(sens_all))))))
        chk("fixed sets inside the primary pool", lambda: (L.assert_pool(P.FIXED3, "primary"), L.assert_pool(P.FIXED6, "primary")))
        chk("model inputs contain no enforced-excluded column", lambda: L.assert_pool(names[1:], "primary"))
        chk("all sessions used are TRAIN partition, LEGACY era", lambda: (L.assert_train_only(ERA, [d["day"][d["first"][i]] for i in np.r_[seg["train"], seg["val"], seg["test"]]]), L.assert_single_era(d, ERA)))
        for bad in ("overnight_return_open", "raw_volume", "log_raw_volume", "raw_volume__sadj", "tlt_return_1m", "lee_mykland_jump60", "jump_variation_15__sadj"):
            try: L.assert_pool(primary + [bad], "primary"); ex[f"negative control {bad}"] = "FAIL: not rejected"
            except AssertionError: ex[f"negative control {bad}"] = "PASS"
        out["checks"]["exclusions"] = ex
        # ---- fold isolation
        iso = {}; day = lambda i: str(d["day"][d["first"][i]])
        tr, va, te = seg["train"], seg["val"], seg["test"]
        iso["train/val/test disjoint and ordered"] = "PASS" if (tr.max() < va.min() and va.max() < te.min() and not (set(tr) & set(va)) and not (set(va) & set(te))) else "FAIL"
        iso["embargo >= 5 sessions between segments"] = "PASS" if (va.min() - tr.max() > 5 and te.min() - va.max() > 5) else "FAIL"
        iso["validation and test sessions equal the fold table's dates after dropping 5"] = "PASS" if (day(va[0]) > str(seg["row"]["inner_validation_first"]) and day(te[-1]) == str(seg["row"]["outer_development_last"])) else "FAIL"
        iso["no session after the fold's last test day is used"] = "PASS" if max(tr.max(), va.max(), te.max()) == te.max() else "FAIL"
        d_tr_end = int(tr.max()); late = [i for i in range(len(native)) if i > d_tr_end]
        feats0 = {k: v.copy() for k, v in d["features"].items()}
        cut = int(d["first"][d_tr_end + 1])
        for k in d["features"]: d["features"][k][cut:] = 1e9                      # overwrite every feature value after the inner-train segment
        Mx2 = Mx.copy(); Mx2[d_tr_end + 1:] = 1e9
        rows_a = [dict(native[i], X=F.deseason(native[i]["X"], F.ret5_scale(Mx, i))) for i in tr]
        rows_b = []
        for i in tr:
            r = L.session_grid(d, i, cols); rows_b.append(dict(r, X=F.deseason(r["X"], F.ret5_scale(Mx2, i))))
        pa = L.Prep().fit(np.vstack([r["X"] for r in rows_a]), names); pb = L.Prep().fit(np.vstack([r["X"] for r in rows_b]), names)
        for k in d["features"]: d["features"][k][:] = feats0[k]
        same = all(getattr(pa, a_) == getattr(pb, a_) for a_ in ("lo", "hi", "mu", "sd", "log", "amihud", "keep"))
        iso["Prep and deseason fit on inner train are unchanged when every later session is overwritten with 1e9"] = "PASS" if (same and np.array_equal(rows_a[-1]["X"], rows_b[-1]["X"], equal_nan=True)) else "FAIL"
        out["checks"]["fold_isolation"] = iso
        to_des = lambda r, sess: dict(r, X=F.deseason(r["X"], F.ret5_scale(Mx, sess)))
        rows = {k: [to_des(native[i], i) for i in seg[k]] for k in ("train", "val", "test")}
        prep = L.Prep().fit(np.vstack([r["X"] for r in rows["train"]]), names)
        mk = lambda r, sub: L.build_sequence(dict(r, X=prep.transform(r["X"])[:, [prep.keep.index(L.RET_NAME)] + [prep.keep.index(x) for x in sub]]))
        # ---- missing data
        md = {}; n_bars = np.array([int(d["end"][i] - d["first"][i]) for i in range(len(d["first"]))]); fin = np.array([np.isfinite(d["close"][d["first"][i]:d["end"][i]]).mean() for i in range(len(d["first"]))])
        fs = np.r_[tr, va, te]
        md["fold sessions"] = len(fs); md["full 390-bar sessions"] = int((n_bars[fs] == 390).sum()); md["early-close / short sessions (bars != 390)"] = int((n_bars[fs] != 390).sum())
        md["sessions with < 98% finite closes"] = int((fin[fs] < 0.98).sum()); md["min finite-close share"] = round(float(fin[fs].min()), 4)
        md["bars with invalid flag (share of fold bars)"] = round(float(1 - np.mean(np.concatenate([d["valid"][d["first"][i]:d["end"][i]] for i in fs]))), 5)
        for k in ("train", "val", "test"):
            q = [mk(r, []) for r in rows[k]]; tot = sum(x["n"] for x in q); real = sum(int(x["real"][:x["n"]].sum()) for x in q)
            md[f"{k}: decision updates / skipped (base set)"] = f"{tot} / {tot-real} ({(tot-real)/tot:.4f})"
            q3 = [mk(r, P.FIXED3) for r in rows[k]]; real3 = sum(int(x["real"][:x["n"]].sum()) for x in q3); md[f"{k}: skipped share (f3 set)"] = round((tot - real3) / tot, 4)
            md[f"{k}: non-finite inputs at real updates (must be 0)"] = int(sum(int((~np.isfinite(x["X"][:x["n"]][x["real"][:x["n"]]])).sum()) for x in q3))
        out["missing_data_summary"] = md
        out["checks"]["missing_data"] = dict(zip(("finite inputs at all real updates",), ["PASS" if all(md[f"{k}: non-finite inputs at real updates (must be 0)"] == 0 for k in ("train", "val", "test")) else "FAIL"]))
        # ---- fits (checkpointed)
        models = {}
        for fam in B.FAMS:
            for sname, sub in B.SETS.items():
                def fit(fam=fam, sub=sub):
                    tr_ = [mk(r, sub) for r in rows["train"]]; m = V.make_model(fam, K=3, lam=39, starts=1, seed=0, Dmax=78); m.fit(L.pad(tr_, 1 + len(sub))); return m
                m, sec = unit(f"fit|{ERA}|{FOLD}|{fam}|{sname}", fit); models[(fam, sname)] = (m, sub, sec)
        out["fit_seconds"] = {f"{k[0]}|{k[1]}": round(v[2], 2) for k, v in models.items()}; ST["fit_all"] = round(sum(v[2] for v in models.values()), 1); log("fits done")
        # ---- causal timing
        ct = {}; i5 = int(seg["val"][5])
        ct["deseason scale ignores later sessions"] = "PASS" if np.array_equal(F.ret5_scale(Mx, i5), F.ret5_scale(np.vstack([Mx[:i5], np.full((len(Mx) - i5, 78), 1e9)]), i5)) else "FAIL"
        ct["deseason scale = scale on truncated history"] = "PASS" if np.array_equal(F.ret5_scale(Mx, i5), F.ret5_scale(Mx[:i5], i5), equal_nan=True) else "FAIL"
        pre_bad = []; nonfin = 0; skip_alarm = 0
        for (fam, sname), (m, sub, _) in models.items():
            qs = [mk(r, sub) for r in rows["val"][:6]]; D = 1 + len(sub); full = V.run_filter(fam, m, qs, D)
            cutq = [dict(q, n=q["n"] // 2, X=q["X"][:q["n"] // 2], real=q["real"][:q["n"] // 2], avail=q["avail"][:q["n"] // 2], slots=q["slots"][:q["n"] // 2], tgt=q["tgt"][:q["n"] // 2]) for q in qs]
            part = V.run_filter(fam, m, cutq, D); key = "pcp" if fam == "bocpd" else "P"
            for a, b_, q in zip(full, part, cutq):
                if not np.allclose(a[key][:q["n"]], b_[key][:q["n"]], rtol=1e-12, atol=1e-14): pre_bad.append(f"{fam}|{sname}")
        ct["filtered output at update t independent of later updates (4 families x 2 sets)"] = "PASS" if not pre_bad else f"FAIL: {sorted(set(pre_bad))}"
        bad_t = n_ev = 0
        for (fam, sname), (m, sub, _) in models.items():
            qs = [mk(r, sub) for r in rows["val"]]; res = V.run_filter(fam, m, qs, 1 + len(sub)); thr = 2.2 if fam != "bocpd" else 3.0; key = "pcp" if fam == "bocpd" else "P"
            for q, r, i in zip(qs, res, seg["val"]):
                nonfin += int((~np.isfinite(np.asarray(r[key])[:q["n"]])).sum())
                a = int(d["first"][i])
                for e in B.events(fam, r, q, thr):
                    n_ev += 1
                    if not q["real"][e["i_c"]]: skip_alarm += 1
                    if not (q["avail"][e["i_c"]] == d["t"][a + q["slots"][e["i_c"]]] + 60 * 10 ** 9 and e["i_c"] - e["i_d"] >= (2 if fam != "bocpd" else 3) and q["avail"][e["i_d"]] < q["avail"][e["i_c"]]): bad_t += 1
        ct[f"alarm time = bar stamp + 1 min, T_c after T_d by >= hold ({n_ev} events checked)"] = "PASS" if bad_t == 0 else f"FAIL: {bad_t}"
        ct["no alarm confirmed on a skipped update"] = "PASS" if skip_alarm == 0 else f"FAIL: {skip_alarm}"
        out["checks"]["causal_timing"] = ct; out["checks"]["missing_data"]["filter outputs finite on all validation sessions (8 detectors)"] = "PASS" if nonfin == 0 else f"FAIL: {nonfin}"
        pi = P.integrity(d, seg, cols, CK); ct["splice integrity on real LEGACY data (3 splices, 8 checks each)"] = "PASS" if all(x["checks"]["pass"] for x in pi) else "FAIL"
        log("exclusion/isolation/timing checks done")
        # ---- Section 6 bisection (checkpointed)
        for (fam, sname), (m, sub, _) in models.items():
            def bis(fam=fam, sub=sub, m=m):
                D = 1 + len(sub); kind = "bocpd" if fam == "bocpd" else "hmm"; lo, hi, tol = B.BOUNDS[kind]
                qv = [mk(r, sub) for r in rows["val"]]; rv_ = V.run_filter(fam, m, qv, D); qt = [mk(r, sub) for r in rows["test"]]; rt_ = V.run_filter(fam, m, qt, D); calls = [0]
                def rate(thr): calls[0] += 1; return sum(len(B.events(fam, r, q, thr)) for q, r in zip(qv, rv_)) / len(qv)
                thr, info = B.bisect_threshold(rate, lo, hi, B.TARGET, tol); vr = rate(thr); tr_ = sum(len(B.events(fam, r, q, thr)) for q, r in zip(qt, rt_)) / len(qt)
                return dict(threshold=thr, info=info, validation_rate=vr, test_rate_realized=tr_, target=B.TARGET, rate_evaluations=calls[0], n_val=len(qv), n_test=len(qt))
            v, sec = unit(f"bis|{ERA}|{FOLD}|{fam}|{sname}", bis); v["seconds"] = round(sec, 1); out["calibration"][f"{fam}|{sname}"] = v
        ST["section6_bisection"] = round(sum(v["seconds"] for v in out["calibration"].values()), 1); log("bisection done")
        # ---- stable days, splices (chunked, checkpointed)
        stable_val, _ = S.stable_days(d, seg["val"], dv); stable_test, _ = S.stable_days(d, seg["test"], dv)
        out["stable_days"] = dict(validation=len(stable_val), test=len(stable_test), evaluable=len(stable_test) >= 8)
        rng = np.random.default_rng(4242)
        sp_val = A.build_specs(d, dv, stable_val, rng, A.N_CAL_NULL, A.CAL_CELLS, A.N_CELL); cells_all = [(R, dr, du) for R in B.SIZES for dr in B.DIRS for du in B.DURS]
        sp_test = A.build_specs(d, dv, stable_test, rng, A.N_NULL, cells_all, A.N_CELL); specs = sp_val + sp_test
        chunks = [(ci, specs[ci * CHUNK:(ci + 1) * CHUNK]) for ci in range((len(specs) + CHUNK - 1) // CHUNK)]
        have = {ci: CK.path(f"splice_chunk|{ERA}|{FOLD}|{ci}|{len(specs)}").exists() for ci, _ in chunks}; todo = [c for c in chunks if not have[c[0]]]
        out["splice_chunks"] = dict(total=len(chunks), already_checkpointed_at_start=sum(have.values()), computed_in_this_run=len(todo))
        log(f"{len(specs)} splices in {len(chunks)} chunks; {sum(have.values())} already checkpointed")
        t0 = time.perf_counter(); done_sec = 0.0
        if todo:
            with mp.get_context("spawn").Pool(WORKERS, initializer=_init, initargs=(cols,)) as pool:
                mem.pids = [p.pid for p in pool._pool]
                for ci, rr in pool.imap_unordered(_work_chunk, todo):
                    CK.run(f"splice_chunk|{ERA}|{FOLD}|{ci}|{len(specs)}", lambda rr=rr: (rr, 0.0)); log(f"chunk {ci} stored")
            mem.pids = []
        out["splice_wall_seconds_this_run"] = round(time.perf_counter() - t0, 1)
        rows_all = [r for ci, _ in chunks for r in CK.run(f"splice_chunk|{ERA}|{FOLD}|{ci}|{len(specs)}", lambda: None)[0]]
        assert len(rows_all) == len(specs)
        rv_rows, rt_rows = rows_all[:len(sp_val)], rows_all[len(sp_val):]
        group = lambda sp, rr: {c: [r for s_, r in zip(sp, rr) if s_["cell"] == c] for c in {s_["cell"] for s_ in sp}}
        gv, gt = group(sp_val, rv_rows), group(sp_test, rt_rows); des = lambda rl: [to_des(r, r["iA"]) for r in rl]
        # ---- H1(a) sweep (vectorised), checkpointed per detector
        for (fam, sname), (m, sub, _) in models.items():
            def sweep(fam=fam, sub=sub, m=m):
                D = 1 + len(sub); grid = B.MGRID if fam == "bocpd" else B.THETA
                def run_(rl):
                    qs = [mk(r, sub) for r in des(rl)]; rs = V.run_filter(fam, m, qs, D); R_, real, av = W.stack(rs, qs, "rstar" if fam == "bocpd" else "P"); return R_, real, av, np.array([r["tau"] for r in rl], np.int64)
                sw = (lambda a, b, c, t: W.sweep_map(a, b, c, grid, t)) if fam == "bocpd" else (lambda a, b, c, t: W.sweep_old_state(a, b, c, grid, t))
                Rn, rn_, an, _ = run_(gv["null"]); cnt, _ = sw(Rn, rn_, an, None); cal_null = (cnt > 0).mean(0); feas = [g for g in range(len(grid)) if cal_null[g] <= 0.10]; cb = np.zeros(len(grid))
                if feas:
                    hd = []
                    for dr in B.DIRS:
                        rl = [r for c, v in gv.items() if c != "null" and c[1] == dr for r in v]; Rb, rb_, ab, tb = run_(rl); _, h = sw(Rb, rb_, ab, tb); hd.append(h.mean(0))
                    cb = np.mean(hd, axis=0)
                run2 = grid[max(feas, key=lambda g: (cb[g], -g))] if feas else None
                Rn, rn_, an, _ = run_(gt["null"]); cnt, _ = sw(Rn, rn_, an, None); xs = cnt.mean(0); hc = {}
                for c, v in gt.items():
                    if c == "null": continue
                    Rb, rb_, ab, tb = run_(v); _, h = sw(Rb, rb_, ab, tb); hc[c] = (h.sum(0), len(v))
                byr = {}
                for Rr in B.SIZES + ["all"]:
                    num = sum(h for c, (h, n) in hc.items() if Rr == "all" or c[0] == Rr); den = sum(n for c, (h, n) in hc.items() if Rr == "all" or c[0] == Rr); pts = list(zip(xs.tolist(), (num / den).tolist()))
                    byr[str(Rr)] = dict(pauc_0_0p5=A.pauc(pts), hit_at_alarm_rate_0p1=A.y_at(pts, 0.1), hit_at_alarm_rate_0p2=A.y_at(pts, 0.2), n_breaks=int(den))
                return dict(by_ratio=byr, run2_threshold=(None if run2 is None else float(run2)), run2_feasible=run2 is not None, smallest_null_alarm_rate_in_sweep=float(xs.min()), x_values_in_0_0p5=int((xs <= 0.5).sum()))
            v, sec = unit(f"sweep|{ERA}|{FOLD}|{fam}|{sname}", sweep); v["seconds"] = round(sec, 1); out["scoring"][f"{fam}|{sname}"] = v; log(f"swept {fam}|{sname}")
        ST["h1a_sweep"] = round(sum(v["seconds"] for v in out["scoring"].values()), 1)
        out["peak_memory"] = dict(parent_peak_mb=peak_mb(), worker_peak_mb=sorted(mem.child_peak.values()), min_system_free_mb=round(mem.min_free))
    out["checkpoint"] = dict(hits=CK.hits, misses=CK.misses); out["wall_minutes_this_run"] = round((time.time() - T0) / 60, 2)
    (RES / f"legacy_pilot_results_{tag}.json").write_text(json.dumps(out, indent=1, default=float)); log(f"done; hits {CK.hits} misses {CK.misses}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    {"build": build, "run": run}[mode]()
