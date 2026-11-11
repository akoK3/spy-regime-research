#!/usr/bin/env python3
"""AMENDMENT_A37 rule 1: the TRAIN refits of the final setups at the 5.12 freeze, outside the frozen result-module closure (code version a0323ed24d68e896).
Per era and family (all four): the frozen final setup and the return-only baseline with its frozen parameters, fitted on every TRAIN session of the era (3 starts,
seed 0); the preprocessing fitted on TRAIN rows; the baseline's era-level threshold by the A11 rule on TRAIN; the feature threshold recomputed by the same rule
(a reproduction value). TRAIN sessions only, through the audited Section 4 loader; every session is checked against the split manifest.
One pickle per era and family, a manifest with a sidecar; the hashes enter the freeze document as input_hashes["frozen_models"] through FreezeBackend, a delegating
wrapper around the main backend (s5_run.freeze_step stores whatever backend.input_hashes() returns; no closure module changes, A26 2c).
  freeze_with_models(backend, summ, results_dir, amendments): the freeze step under A37 (verify the completion record, fit and save, then s5_run.freeze_step).
The evaluation step loads these files only (s5_eval513.load_frozen). Nothing here reads an evaluation or embargo session."""
import sys, json, pickle, hashlib, datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
FROZEN_DIR = HERE / "results" / "frozen_models"; MANIFEST_NAME = "manifest.json"


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def manifest_path(d=None): return Path(d or FROZEN_DIR) / MANIFEST_NAME
def file_name(era, family): return f"{era}_{family}.pkl"


def train_state(era):
    """Context and backends of one era over its TRAIN sessions only (A37 1c)."""
    import s5_eval_loader as EL, s5_eval513 as S513
    EL.check_dev_spans(); d = S513._load_span(era, *EL.DEV[era]); d["era"] = era; days = [str(d["day"][i]) for i in d["first"]]
    part = S513.partitions(era); tr = sorted(x for x, p in part.items() if p == "TRAIN")
    if days != tr:
        extra = [x for x in days if x not in set(tr)][:3]; miss = [x for x in tr if x not in set(days)][:3]
        raise PermissionError(f"{era}: the freeze-time panel is not exactly the TRAIN sessions of the split manifest (A37 1c): {len(days)} panel sessions, {len(tr)} TRAIN; not TRAIN {extra}; missing {miss}")
    return S513.build_state(era, d, len(days)), days


def fit_bundles(era, setups_era):
    """{family: bundle} of one era (A37 1b). setups_era: {family: final setup of the freeze}."""
    import s5_h1 as H, s5_eval513 as S513, s5_guard as G
    st, days = train_state(era); db = st["full"]; out = {}; cv = G.code_version()
    for fam in H.FAMILIES:
        s = setups_era[fam]; feats = tuple(s["features"]); par = dict(s["params"]); bp = dict(s.get("base_params") or s["params"])
        mf = db.fit(fam, feats, par, 3); mb = db.fit(fam, (), bp, 3)
        tb, rb = S513.calibrate(st, fam, (), bp); tf, rf = S513.calibrate(st, fam, feats, par)
        out[fam] = dict(era=era, family=fam, setup=s, features=list(feats), params=par, base_params=bp, feature=mf, baseline=mb, prep=db.c["prep"],
                        thresholds=dict(baseline_a11=tb, baseline_calibration_rate=rb, feature_recomputed=tf, feature_recomputed_rate=rf),
                        code_version=cv, n_train=len(days), train_first=days[0], train_last=days[-1], fitted_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    return out


def write_models(final_setups, out_dir=None):
    """Fits, saves and hashes every era and family (A37 1b, 1d). Written once: refuses if a manifest exists. Returns the freeze record (frozen_hashes)."""
    d = Path(out_dir or FROZEN_DIR); mp = manifest_path(d)
    if mp.exists(): raise FileExistsError(f"{mp} exists: frozen models are written once")
    d.mkdir(parents=True, exist_ok=True); files = {}
    for era in sorted(final_setups):
        for fam, b in fit_bundles(era, final_setups[era]).items():
            p = d / file_name(era, fam); tmp = p.with_suffix(".tmp"); tmp.write_bytes(pickle.dumps(b, protocol=4)); tmp.replace(p); files[p.name] = sha(p)
    import s5_guard as G
    man = dict(kind="a37_frozen_models", created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), code_version=G.code_version(), eras=sorted(final_setups), files=files)
    mp.write_text(json.dumps(man, indent=1), encoding="utf-8"); G.write_side(mp); return frozen_hashes(d)


def frozen_hashes(out_dir=None):
    """The record the freeze document carries: the manifest's sha256 and every file's sha256 (A37 1e)."""
    mp = manifest_path(out_dir); side = mp.with_suffix(".sha256")
    if not side.exists() or side.read_text().split()[0] != sha(mp): raise PermissionError("frozen-model manifest missing or differs from its sidecar")
    return dict(manifest_sha256=sha(mp), files=json.loads(mp.read_text(encoding="utf-8"))["files"], rule="AMENDMENT_A37 rule 1")


class FreezeBackend:
    """Delegates everything to the main backend; input_hashes() adds the frozen-model record (A37 1e)."""
    def __init__(self, backend, models): self._b = backend; self._models = models
    def __getattr__(self, n): return getattr(self._b, n)
    def input_hashes(self): h = dict(self._b.input_hashes()); h["frozen_models"] = self._models; return h


def freeze_with_models(backend, summ, results_dir, amendments):
    """The 5.12 freeze under A37: completion record verified, models fitted and saved (TRAIN only), then the unchanged s5_run.freeze_step with the wrapper."""
    import s5_guard as G, s5_run as RUN, s5_freeze as FZ
    if (Path(results_dir) / "section5_freeze.json").exists(): raise FileExistsError("a freeze exists")
    if list(Path(results_dir).glob(FZ.EVAL_PREFIX + "*")): raise RuntimeError("evaluation output exists; the freeze must precede it (5.12)")
    G.verify_completion(Path(summ["run_dir"]) / G.COMPLETION, require_main=(getattr(backend, "kind", None) == "main"))
    models = write_models(summ["final_setups"])
    return RUN.freeze_step(FreezeBackend(backend, models), summ, results_dir, amendments)
