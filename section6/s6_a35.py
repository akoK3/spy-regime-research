#!/usr/bin/env python3
"""AMENDMENT_A35 rule 2: rerun of the A28 7d(ii) null control, exactly as pre-registered and as run in the development run: 200 null sets (index 0..199), the same
seeds (null-control seed 7; unit, placebo and bootstrap seeds as s6_run.null_set), the resample count of the development run (9,999), the six primary tests, with the
A35 rule 1 p-value for H4a and H4b (valid resamples only). No extra sets, no recalibration; nothing else is recomputed. Development data only.
Units, candidates and placebos are built exactly as in s6_run.analyse. Each set also records the p-value under the A29 1d convention from the same resamples; the
rejection rates under that convention must equal the stored development-run rates exactly (rule 2d reproduction check), else the rerun is not used (exit 4).
Criterion (A28 7d, unchanged): for each of the six tests the share of sets with p <= 0.05 is at most 0.10. The output states which of A35 3a / 3c / 3d applies.
Sets are appended to a35_null_reps_DETECTOR.jsonl as they finish (a restart resumes; every set is deterministic given its index).
Usage: s6_a35.py null DETECTOR [--workers N]     Output (written once): section6/results/a35_null_control_DETECTOR.json"""
import sys, json, time, datetime
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "section5"))
import s6_run as R

AMENDMENTS = ("A28", "A29", "A30", "A31", "A32", "A33", "A33_1", "A34", "A35"); N_SETS = 200; SEED = 7; LIMIT = 0.10; DETS = ("gaussian_hmm", "hsmm")


def summarise(det, sets, stored):
    """sets: {index: {test: dict(p, p_a29_1d)}} for all N_SETS indices; stored: the development run's sanity.null_control."""
    rej = lambda key: {k: float(np.mean([sets[s][k][key] is not None and sets[s][k][key] <= 0.05 for s in range(N_SETS)])) for k in R.PRIMARY}
    rate, old = rej("p"), rej("p_a29_1d")
    repro = stored["n_sets"] == N_SETS and all(abs(old[k] - stored["rejection_rate"][k]) < 1e-12 for k in R.PRIMARY)
    passed = all(v <= LIMIT for v in rate.values()); over = [k for k in R.PRIMARY if rate[k] > LIMIT]
    if not repro: cons = "A35 2d: the A29 1d rates do not reproduce the development run; the rerun is not used; work stops"
    elif det == "gaussian_hmm": cons = ("A35 3c: the Gaussian HMM passes; nothing changes (A28 1b stands)" if passed else
                                        "A35 3a: the Gaussian HMM exceeds 0.10 on " + ", ".join(over) + "; it is ineligible as the H3/H4 primary detector; the HSMM is the H3/H4 primary; the Gaussian HMM remains eligible for H2 by the 5.12 freeze rule")
    else: cons = ("the HSMM passes" if passed else "A35 3d: the HSMM exceeds 0.10 on " + ", ".join(over) + "; A28 7d applies as written: work stops before the joint evaluation and the user decides")
    return dict(rejection_rate=rate, limit=LIMIT, passed=bool(passed), tests_over_limit=over, rejection_rate_a29_1d_convention=old, development_run_rejection_rate=stored["rejection_rate"],
                reproduces_development_run=bool(repro), consequence=cons)


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] != "null" or a[1] not in DETS: print(__doc__); return 3
    det = a[1]; workers = int(a[a.index("--workers") + 1]) if "--workers" in a else 1
    R.a29_guard(AMENDMENTS)
    import s5_contamination as CT, s6_fingerprint as FP, s5_amendment_manifest as AM
    CT.check_registry()                                                             # section5 and section6 (FABLE_REAUDIT L1: a runtime call, not only a unit test)
    out = R.OUT / f"a35_null_control_{det}.json"; part = R.OUT / f"a35_null_reps_{det}.jsonl"
    if out.exists(): print("result exists; written once"); return 3
    prov = dict(code=FP.current(), amendments=AM.manifest(AMENDMENTS))             # taken at the start: the code this process loaded
    dev = json.loads((R.OUT / f"s6_development_{det}.json").read_text(encoding="utf-8")); stored = dev["sanity"]["null_control"]; nboot = int(dev["nboot"])
    rows, sess = R.load_breaks(det); E_by = {era: R.load_era(era, "development") for era in ("LEGACY", "RAW")}
    units, cand_by, alarms_by = [], {}, {}
    for era, E in E_by.items():                                                     # as s6_run.analyse
        u, c, al = R.build(E, rows, sess); units += R.attach_placebos(u, c, al); cand_by[era], alarms_by[era] = c, al
    R.fed_flags(units)
    sets = {}
    if part.exists():
        for line in part.read_text(encoding="utf-8").splitlines(): r = json.loads(line); sets[int(r["set"])] = r["tests"]
    todo = [s for s in range(N_SETS) if s not in sets]; t0 = time.time(); print(f"{len(todo)} null sets to run ({len(sets)} done); nboot {nboot}; workers {workers}", flush=True)
    extra = dict(units=units, cand_by=cand_by, alarms_by=alarms_by, nboot=nboot, seed=SEED, detail=True)
    with open(part, "a", encoding="utf-8") as f:
        def keep(s, r):
            sets[s] = r; f.write(json.dumps(dict(set=s, tests=r)) + "\n"); f.flush()
            if len(sets) % 10 == 0 or len(sets) == N_SETS: print(f"{len(sets)}/{N_SETS} {time.time() - t0:.0f} s", flush=True)
        if workers <= 1:
            R._winit(E_by, extra)
            for s in todo: keep(s, R._wtask(("null", s)))
        else:
            import multiprocessing as mp
            with mp.get_context("spawn").Pool(workers, initializer=R._winit, initargs=(E_by, extra)) as pool:
                for s, r in zip(todo, pool.imap(R._wtask, [("null", s) for s in todo], chunksize=1)): keep(s, r)
    res = dict(detector=det, label="AMENDMENT_A35 rule 2: rerun of the A28 7d(ii) null control (H4 p on valid resamples only, A35 rule 1); development data", period="development",
               n_sets=N_SETS, seed=SEED, nboot=nboot, **summarise(det, sets, stored), sets={str(s): sets[s] for s in range(N_SETS)},
               development_result_sha256=__import__("hashlib").sha256((R.OUT / f"s6_development_{det}.json").read_bytes()).hexdigest(),
               seconds_this_process=round(time.time() - t0, 1), generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), provenance=prov)
    print(f"written {R.write_once(out, res)}"); print(json.dumps({k: res[k] for k in ("rejection_rate", "passed", "reproduces_development_run", "consequence")}, indent=1))
    return 0 if res["reproduces_development_run"] else 4


if __name__ == "__main__": sys.exit(main())
