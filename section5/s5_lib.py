#!/usr/bin/env python3
"""Section 5 library: data, folds, inner-train-only preprocessing, enforced exclusions, checkpointing, decision grid.
Protocol: SECTION5_PROTOCOL.md (DRAFT pending pilot). Reads TRAIN-partition sessions only (asserted)."""
import sys, os, json, hashlib, pickle, time, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.simplefilter("ignore")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
R = ROOT / "section431_step3_all_in_one_results"
FZ = ROOT / "frozen_documents"
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)

GRID = 5                      # decision bars every 5 min, stamped minute 4, 9, ...
FIRST_SLOT = 4
EMBARGO = 5                   # sessions
WINSOR = (0.5, 99.5)
HORIZON = 60                  # QLIKE target: next 60 one-minute bars
QLIKE_FLOOR = 1e-10
RESPONSE_TOKENS = ("TLT", "HYG", "GLD", "GOLD", "USD", "UUP", "DXY")
ENFORCED_EXCLUDED = ("overnight_return_open", "raw_volume", "log_raw_volume", "raw_volume__sadj")
LM_FLAG = "lee_mykland_jump60"
RET_NAME = "ret5"


# ---------- hashes, checkpointing ----------
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Checkpoint:
    """One pickle per unit of work; a finished unit is never recomputed. The key must encode every input that changes the result."""
    def __init__(self, folder):
        self.dir = Path(folder); self.dir.mkdir(parents=True, exist_ok=True); self.hits = 0; self.misses = 0

    def path(self, key):
        return self.dir / (hashlib.sha256(key.encode()).hexdigest()[:24] + ".pkl")

    def run(self, key, fn):
        p = self.path(key)
        if p.exists():
            self.hits += 1
            with open(p, "rb") as f: return pickle.load(f)["value"]
        self.misses += 1
        v = fn()
        tmp = p.with_suffix(".tmp")
        with open(tmp, "wb") as f: pickle.dump({"key": key, "value": v}, f)
        os.replace(tmp, p)
        return v


# ---------- pools and enforced exclusions ----------
def pools():
    m = pd.read_csv(R / "a4_sec4_3_9_frozen_matrix_v2.csv")
    primary = m.loc[m.primary_outcome == "kept", "column"].tolist()
    sens_all = m.loc[m.sensitivity_outcome == "kept", "column"].tolist()
    sens = [c for c in sens_all if not (c.startswith("jump_variation") and c.endswith("__sadj"))]  # 5.2: jump_variation__sadj dropped
    return primary, sens, sens_all


SCALE_STEMS = ("rv", "downside", "abs_return", "intrabar_range")              # A20 rule 1: scale-type name-stem families (A18 rule 3)


def stem_of(col):
    c = col[:-6] if col.endswith("__sadj") else col
    for stem in ("abs_return", "return", "intrabar_range", "relative_volume", "close_location", "downside", "momentum", "rv"):
        if c.startswith(stem): return stem
    return None


def a20_pool(cols):
    """A20 rule 1: scale-type columns only in their __sadj versions (raw scale columns excluded); other columns unchanged."""
    return [c for c in cols if stem_of(c) not in SCALE_STEMS or c.endswith("__sadj")]


def assert_pool(cols, kind, response_names=()):
    """kind: 'primary' or 'sensitivity'. Enforces every 5.2 exclusion on the column names that reach a model."""
    cols = list(cols)
    assert len(set(cols)) == len(cols), "duplicate columns"
    bad = [c for c in cols if c in ENFORCED_EXCLUDED]
    assert not bad, f"enforced exclusion violated: {bad}"
    assert not [c for c in cols if c.startswith("overnight")], "overnight column in detector inputs"
    assert not [c for c in cols if any(t in c.upper() for t in RESPONSE_TOKENS) or c in response_names], "response asset column in detector inputs"
    assert not [c for c in cols if c.startswith("jump_variation") and c.endswith("__sadj")], "jump_variation__sadj must be dropped"
    primary, sens, _ = pools()
    if kind == "primary":
        assert LM_FLAG not in cols, "Lee-Mykland flag is sensitivity-only"
        assert not [c for c in cols if c.startswith("lee_mykland")], "Lee-Mykland columns are sensitivity-only"
        assert set(cols) <= set(primary), "column outside primary 19"
    else:
        assert set(cols) <= set(sens), "column outside the sensitivity set"
    return True


def assert_train_only(era, days, manifest=None):
    """All sessions used must be TRAIN rows of this era in the split manifest (no embargo, evaluation, excluded or other-era sessions)."""
    mf = manifest if manifest is not None else pd.read_csv(FZ / "section430_executable_split_manifest.csv")
    part = mf[mf.provider_era == era].set_index("session_date").partition
    days = list(days)
    unknown = [x for x in days if x not in part.index]; assert not unknown, f"sessions not in manifest for {era}: {unknown[:3]}"
    bad = [x for x in days if part[x] != "TRAIN"]; assert not bad, f"non-TRAIN sessions used: {bad[:3]}"
    return True


def assert_single_era(d, era):
    assert d["era"] == era, "cross-era rows"
    return True


# ---------- data ----------
def _step3():
    import step3_all_in_one as s
    return s


def load_era(era, columns):
    """Development panel (TRAIN span) plus the requested feature columns (cached as float64 npz; features computed from the panel by the audited code)."""
    s = _step3()
    f, l, p, e = s.CONFIG[era]
    spec = {"first_session": f, "last_session": l, "panel_file": str(s.file_path(p)), "etf_file": str(s.file_path(e))}
    d = s.load_development(era, spec); d.update(s.load_ohlc(spec, d)); d["era"] = era
    assert_train_only(era, sorted(set(d["day"])))
    cf = CACHE / f"{era}_features.npz"
    have = dict(np.load(cf)) if cf.exists() else {}
    need = [c for c in columns if c not in have]
    if need:
        have.update(compute_features(d, need)); np.savez(cf, **have)
    d["features"] = {c: have[c] for c in columns}
    return d


def compute_features(d, names):
    """Features for the requested names from the panel dict d (same code as Section 4; __sadj via the causal 20-session baseline)."""
    import step11_a4_rerun_4_3_4_7_8 as p
    s = _step3()
    flat = {}
    a, _ = s.construct(d); flat.update(a)
    b = s.construct_additions(dict(d)); flat.update(b); flat.update(s.construct_deferred(d))
    out = {}
    for n in names:
        if n.endswith("__sadj"): out[n] = p.adjust(np.asarray(flat[n[:-6]], float), d["slot"], d["first"], d["end"])
        else: out[n] = np.asarray(flat[n], float)
    return out


def sub_panel(d, sess):
    """Panel dict restricted to a list of session indices (rows are re-based)."""
    idx = np.concatenate([np.arange(d["first"][i], d["end"][i]) for i in sess])
    lens = [int(d["end"][i] - d["first"][i]) for i in sess]
    first = np.r_[0, np.cumsum(lens)[:-1]]
    out = {k: v[idx] for k, v in d.items() if isinstance(v, np.ndarray) and v.shape[:1] == (len(d["t"]),)}
    out.update(first=first.astype(np.int64), end=(first + lens).astype(np.int64), era=d["era"])
    return out


# ---------- folds ----------
def fold_segments(d, era, fold):
    """Inner train / validation / test session indices of one A4 fold. 5-session embargoes: validation and test each lose their first 5 sessions
    (the embargo sits between segments, so no embargo session is used)."""
    f = pd.read_csv(R / "a4_development_nested_folds_TRAIN.csv"); f = f[(f.era == era) & (f.fold == fold)].iloc[0]
    days = np.array([d["day"][i] for i in d["first"]])
    sel = lambda a, b: np.where((days >= a) & (days <= b))[0]
    tr, va, te = sel(f.inner_train_first, f.inner_train_last), sel(f.inner_validation_first, f.inner_validation_last), sel(f.outer_development_first, f.outer_development_last)
    assert len(tr) == f.inner_train_sessions and len(va) == f.inner_validation_sessions and len(te) == f.outer_sessions
    va, te = va[EMBARGO:], te[EMBARGO:]
    assert tr.max() + EMBARGO < va.min() and va.max() + EMBARGO < te.min()
    assert_train_only(era, days[np.r_[tr, va, te]])
    return dict(train=tr, val=va, test=te, embargo=EMBARGO, row={k: (v.item() if hasattr(v, "item") else v) for k, v in f.to_dict().items()})


# ---------- preprocessing (inner train only) ----------
class Prep:
    """Fitted on inner-train rows only: zero-variance drop (5.7), Amihud level normalization, log if strictly positive in inner train,
    winsorization at 0.5/99.5, z-score. The 5-minute return and signed features are never logged."""
    NO_LOG = ("return_1m", "momentum", "close_location", "ret5", "overnight")

    def fit(self, X, names):
        self.names = list(names); self.keep = []; self.info = {}
        self.amihud, self.log, self.lo, self.hi, self.mu, self.sd = {}, {}, {}, {}, {}, {}
        for j, n in enumerate(names):
            x = X[:, j]; x = x[np.isfinite(x)]
            if len(x) < 10 or np.var(x) == 0: self.info[n] = "dropped: zero variance or too few finite values"; continue
            if n.startswith("amihud"):
                med = float(np.median(x))
                if med > 0: self.amihud[n] = med; x = x / med
            uselog = (not n.startswith(self.NO_LOG)) and bool((x > 0).all())  # log only if strictly positive in inner train
            if uselog: x = np.log(x)
            lo, hi = np.percentile(x, WINSOR); x = np.clip(x, lo, hi)
            if np.var(x) == 0: self.info[n] = "dropped: zero variance after winsorization"; continue
            self.keep.append(n); self.log[n] = uselog; self.lo[n], self.hi[n] = float(lo), float(hi); self.mu[n], self.sd[n] = float(x.mean()), float(x.std())
            self.info[n] = "log" if uselog else "raw"
        return self

    def transform(self, X):
        out = np.full((X.shape[0], len(self.keep)), np.nan)
        for k, n in enumerate(self.keep):
            x = X[:, self.names.index(n)].astype(float).copy()
            if n in self.amihud: x = x / self.amihud[n]
            if self.log[n]:
                pos = x > 0
                x = np.where(pos, np.log(np.where(pos, x, 1.0)), np.nan)  # non-positive out-of-sample value: missing (skipped update)
            out[:, k] = (np.clip(x, self.lo[n], self.hi[n]) - self.mu[n]) / self.sd[n]
        return out


def lm_student_t_threshold(stat, per_session=0.01, tests=390):
    """Lee-Mykland threshold from a Student-t fit to the inner-train statistic (two-sided, per-session false-alarm rate 1%)."""
    from scipy import stats
    x = np.asarray(stat, float); x = x[np.isfinite(x)]
    df, loc, scale = stats.t.fit(x, floc=0.0)
    q = 1.0 - per_session / tests / 2.0
    return dict(df=float(df), scale=float(scale), threshold=float(stats.t.ppf(q, df, loc=0, scale=scale)), n=int(len(x)))


# ---------- decision grid ----------
def grid_slots(m):
    return np.arange(FIRST_SLOT, m, GRID)


def session_grid(d, i, cols):
    """Raw decision-grid rows of one session: 5-minute return + feature columns at the grid bars, availability times, 60-min targets (A20: deseasonalised, from d['dv'])."""
    a, b = int(d["first"][i]), int(d["end"][i]); m = b - a
    g = grid_slots(m); c, o = d["close"][a:b], d["open"][a:b]
    prev = np.where(g - GRID >= 0, c[np.maximum(g - GRID, 0)], o[0])  # slot 4: from the session open
    with np.errstate(invalid="ignore", divide="ignore"):
        ret5 = np.log(c[g] / prev)
    ok = np.isfinite(ret5) & d["valid"][a:b][g]
    ret5 = np.where(ok, ret5, np.nan)
    X = np.column_stack([ret5] + [d["features"][n][a:b][g] for n in cols])
    tgt = np.full(len(g), np.nan)
    if "dv" in d:                                                               # A20 rule 2: deseasonalised target (r^2 / causal slot baseline); no dv -> no target
        r2 = d["dv"][a:b]
        for k, s0 in enumerate(g):
            if s0 + HORIZON <= m - 1:
                w = r2[s0 + 1:s0 + 1 + HORIZON]; n = np.isfinite(w).sum()
                if n >= 50: tgt[k] = max(np.nansum(w) * HORIZON / n, QLIKE_FLOOR)
    return dict(sess=int(i), slots=g, avail=d["available"][a:b][g], X=X, tgt=tgt)


def build_sequence(row):
    """Start at the first grid bar with all features present; abstain before (5.3)."""
    X = row["X"]; full = np.isfinite(X).all(axis=1)
    if not full.any():
        return dict(row, start=None, n=0, X=X[:0], slots=row["slots"][:0], avail=row["avail"][:0], tgt=row["tgt"][:0], real=np.zeros(0, bool), grid_n=len(X))
    s0 = int(np.argmax(full)); Xs = X[s0:]
    return dict(row, start=s0, n=len(Xs), X=Xs, slots=row["slots"][s0:], avail=row["avail"][s0:], tgt=row["tgt"][s0:], real=np.isfinite(Xs).all(axis=1), grid_n=len(X))


def pad(seqs, D):
    """Batch arrays: X (S,T,D) with NaN at skipped/padded steps, real (S,T), L (S,)."""
    S = len(seqs); T = max([q["n"] for q in seqs] + [1])
    X = np.full((S, T, D), np.nan); real = np.zeros((S, T), bool); L = np.zeros(S, int)
    for k, q in enumerate(seqs):
        n = q["n"]; L[k] = n
        if n: X[k, :n] = q["X"]; real[k, :n] = q["real"]
    return dict(X=X, real=real, L=L, S=S, T=T, D=D)


def shares(seqs):
    grid = sum(q["grid_n"] for q in seqs); used = sum(q["n"] for q in seqs); skipped = sum(int((~q["real"]).sum()) for q in seqs)
    return dict(grid_bars=int(grid), abstained_share=round(1 - used / max(grid, 1), 5), skip_share_after_start=round(skipped / max(used, 1), 5), sessions_without_start=int(sum(q["start"] is None for q in seqs)))
