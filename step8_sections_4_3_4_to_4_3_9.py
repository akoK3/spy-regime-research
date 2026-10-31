#!/usr/bin/env python3
"""Sections 4.3.4-4.3.9 exactly per amendment A3 (amendment_4_3_A3_*.json). TRAIN rows only, RAW then LEGACY.

Reads the A3 file (hash checked) for every rule and list. Columns are the 80 detector outputs; overnight_return_open
is excluded. Per-era feature columns are written to a temporary folder outside the repository and deleted at the end.
"""
import sys, json, hashlib, datetime, time, shutil, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.simplefilter("ignore")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import step3_all_in_one as s  # noqa: E402

R = s.OUT
TMP = Path(r"C:\Users\kakij\AppData\Local\Temp\claude\C--Users-kakij-OneDrive-Desktop-data\4f04f2bd-9b49-46e0-9172-37590870166e\scratchpad\sec4349_cols")
START = time.time()
ERAS = ("RAW", "LEGACY")
TRAIN_ROWS = {"LEGACY": 1562460, "RAW": 274050}
SLOTS = 390
THRESHOLD, RUN_LENGTH = 0.95, 5


def log(msg):
    print(f"[{(time.time()-START)/60:6.1f} min] {msg}", flush=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def one(pattern):
    files = sorted(R.glob(pattern))
    assert len(files) == 1, pattern
    return files[0]


A3_FILE = one("amendment_4_3_A3_2*.json")
assert A3_FILE.with_suffix(".sha256").read_text().split()[0] == sha(A3_FILE), "A3 hash mismatch"
A3 = json.loads(A3_FILE.read_text(encoding="utf-8"))
INP = {x["output"]: x for x in A3["redundancy_priority_inputs"]}
NAMES = [x["output"] for x in A3["redundancy_priority_inputs"]]  # dictionary order
SCALE, RAW_ONLY = A3["feature_classes"]["scale_adjusted"], A3["feature_classes"]["raw_only"]
PRIMARY = A3["eligibility_sets"]["primary_20"]
COV = {c["column"]: c for c in json.loads((R / "step6_coverage_TRAIN.json").read_text(encoding="utf-8"))["columns"]}
CLOSING = json.loads(one("section_4_3_1_closing_report_2*.json").read_text(encoding="utf-8"))
DICT = {x["output"]: x for x in CLOSING["feature_dictionary"]}
assert len(NAMES) == 80 and len(SCALE) + len(RAW_ONLY) == 80 and len(PRIMARY) == 20
OUTPUTS = []  # (label, path)


def write(path, text_or_bytes, label):
    p = R / path
    if isinstance(text_or_bytes, str): text_or_bytes = text_or_bytes.encode("utf-8")
    p.write_bytes(text_or_bytes)
    OUTPUTS.append((label, p))
    return p


def write_csv(path, df, label):
    return write(path, df.to_csv(index=False), label)


# ---------------------------------------------------------------- per-era preparation
def prepare_era(era):
    first, last, panel, etf = s.CONFIG[era]
    spec = {"first_session": first, "last_session": last, "panel_file": str(s.file_path(panel)), "etf_file": str(s.file_path(etf))}
    log(f"{era}: loading TRAIN rows")
    d = s.load_development(era, spec)
    d.update(s.load_ohlc(spec, d))
    assert len(d["r"]) == TRAIN_ROWS[era], f"{era} TRAIN rows {len(d['r'])}"
    log(f"{era}: {len(d['r'])} TRAIN rows, {len(d['first'])} sessions; computing features")
    f = s.calculate(d, f"{era} 4.3.4-4.3.9")
    cols = {**f["original"], **f["additional"]}
    del f
    folder = TMP / era
    folder.mkdir(parents=True, exist_ok=True)
    finite = {}
    for n in NAMES:
        x = np.asarray(cols[n], float)
        np.save(folder / f"{n}.npy", x)
        finite[n] = int(np.isfinite(x).sum())
        assert finite[n] == COV[n][f"{era}_finite"], f"{era}.{n}: finite count differs from Step 6"
    del cols
    log(f"{era}: feature columns saved; finite counts equal Step 6 for all 80")
    years = np.array([x[:4] for x in d["day"]])
    return dict(era=era, rows=len(d["r"]), slot=d["slot"].copy(), close=d["close"].copy(), years=years, folder=folder, finite=finite)


def load_col(st, n):
    return np.load(st["folder"] / f"{n}.npy")


def year_slices(st):
    yl = sorted(set(st["years"].tolist()))
    starts = np.searchsorted(st["years"], yl, side="left")
    ends = np.r_[starts[1:], len(st["years"])]
    assert (np.diff(st["years"].astype(int)) >= 0).all()
    return yl, list(zip(starts, ends))


# ---------------------------------------------------------------- 4.3.5 stale closes
def stale_closes(st):
    c, slot = st["close"], st["slot"]
    n = len(c); fin = np.isfinite(c)
    same = np.zeros(n, bool)
    same[1:] = fin[1:] & fin[:-1] & (c[1:] == c[:-1]) & (slot[1:] > 0)
    run_id = np.cumsum(~same)
    length = np.bincount(run_id)[run_id]
    flag = fin & (length >= RUN_LENGTH)
    yl, sl = year_slices(st)
    by_year = pd.DataFrame([dict(era=st["era"], year=y, flagged_bars=int(flag[a:b].sum()), observed_bars=int(fin[a:b].sum()), grid_rows=int(b - a)) for y, (a, b) in zip(yl, sl)])
    by_year["share_of_grid_rows_pct"] = (100 * by_year.flagged_bars / by_year.grid_rows).round(4)
    by_year["share_of_observed_bars_pct"] = (100 * by_year.flagged_bars / by_year.observed_bars).round(4)
    sl_flag = np.bincount(slot[flag], minlength=SLOTS); sl_obs = np.bincount(slot[fin], minlength=SLOTS); sl_all = np.bincount(slot, minlength=SLOTS)
    by_slot = pd.DataFrame(dict(era=st["era"], slot=np.arange(SLOTS), flagged_bars=sl_flag, observed_bars=sl_obs, grid_rows=sl_all))
    by_slot["share_of_grid_rows_pct"] = (100 * by_slot.flagged_bars / by_slot.grid_rows.where(by_slot.grid_rows > 0)).round(4)
    by_slot["share_of_observed_bars_pct"] = (100 * by_slot.flagged_bars / by_slot.observed_bars.where(by_slot.observed_bars > 0)).round(4)
    runs = np.bincount(length[flag & (np.r_[True, ~same[1:]])])
    summary = dict(era=st["era"], flagged_bars=int(flag.sum()), observed_bars=int(fin.sum()), grid_rows=int(n), runs_of_5_or_more=int((flag & (np.r_[True, ~same[1:]])).sum()),
                   longest_run=int(length[flag].max()) if flag.any() else 0,
                   share_of_grid_rows_pct=round(100 * flag.sum() / n, 4), share_of_observed_bars_pct=round(100 * flag.sum() / fin.sum(), 4))
    return summary, by_year, by_slot


# ---------------------------------------------------------------- 4.3.4 seasonality and 4.3.6 yearly stats
def seasonality_and_yearly(st):
    era = st["era"]; slot = st["slot"]
    yl, sl = year_slices(st)
    medians, rows6, problems = {}, [], []
    undefined_slots = {}
    def yearly(name, kind, x):
        fin = np.isfinite(x)
        for y, (a, b) in zip(yl, sl):
            v = x[a:b][fin[a:b]]
            if len(v):
                q1, med, q3 = np.percentile(v, [25, 50, 75])
                rows6.append(dict(era=era, year=y, column=name, kind=kind, n_finite=len(v), n_rows=int(b - a), median=med, iqr=q3 - q1))
            else:
                rows6.append(dict(era=era, year=y, column=name, kind=kind, n_finite=0, n_rows=int(b - a), median=np.nan, iqr=np.nan))
    for k, n in enumerate(NAMES):
        x = load_col(st, n)
        yearly(n, "raw", x)
        if n in SCALE:
            fin = np.isfinite(x)
            m = pd.Series(x[fin]).groupby(slot[fin]).median().reindex(range(SLOTS)).to_numpy()
            populated = np.isfinite(m)
            m = np.where(populated & (m > 0), m, np.nan)
            undefined_slots[n] = int((~np.isfinite(m) & (np.bincount(slot[fin], minlength=SLOTS) > 0)).sum())
            adj = x / m[slot]
            adj_fin = np.isfinite(adj)
            if not (adj_fin == (fin & np.isfinite(m[slot]))).all(): problems.append(f"{n}: NaN pattern of the adjusted column")
            med_adj = pd.Series(adj[adj_fin]).groupby(slot[adj_fin]).median().reindex(range(SLOTS)).to_numpy()
            dev = np.nanmax(np.abs(med_adj[np.isfinite(med_adj)] - 1)) if np.isfinite(med_adj).any() else np.nan
            if not (dev < 1e-9): problems.append(f"{n}: per-slot median of the adjusted column differs from 1 by {dev}")
            medians[n] = m
            yearly(n + "__sadj", "adjusted", adj)
        if (k + 1) % 20 == 0: log(f"{era}: 4.3.4/4.3.6 processed {k+1}/80 columns")
    med_df = pd.DataFrame({"slot": np.arange(SLOTS), **{n: medians[n] for n in SCALE}})
    return med_df, pd.DataFrame(rows6), problems, undefined_slots


# ---------------------------------------------------------------- 4.3.8 Spearman
def spearman_matrix(st, cols, label):
    X = {n: load_col(st, n) for n in cols}
    fin = {n: np.isfinite(X[n]) for n in cols}
    nfin = {n: int(fin[n].sum()) for n in cols}
    own = {}
    def own_rank(n):
        if n not in own: own[n] = pd.Series(X[n][fin[n]]).rank(method="average").to_numpy()
        return own[n]
    m = len(cols)
    rho, overlap = np.full((m, m), np.nan), np.zeros((m, m), dtype=np.int64)
    pairs = m * (m - 1) // 2; done = 0
    for i in range(m):
        rho[i, i] = 1.0; overlap[i, i] = nfin[cols[i]]
        for j in range(i + 1, m):
            a, b = cols[i], cols[j]
            mask = fin[a] & fin[b]; cnt = int(mask.sum()); overlap[i, j] = overlap[j, i] = cnt
            if cnt >= 3:
                ra = own_rank(a) if cnt == nfin[a] else pd.Series(X[a][mask]).rank(method="average").to_numpy()
                rb = own_rank(b) if cnt == nfin[b] else pd.Series(X[b][mask]).rank(method="average").to_numpy()
                ra, rb = ra - ra.mean(), rb - rb.mean()
                den = np.sqrt((ra * ra).sum() * (rb * rb).sum())
                if den > 0: rho[i, j] = rho[j, i] = float((ra * rb).sum() / den)
            done += 1
            if done % 400 == 0: log(f"{label}: Spearman {done}/{pairs} pairs")
    log(f"{label}: Spearman {pairs}/{pairs} pairs done")
    return pd.DataFrame(rho, index=cols, columns=cols), pd.DataFrame(overlap, index=cols, columns=cols)


def redundancy(cols, rhos, coverage_of):
    """Keep a column unless it is redundant (|rho| > 0.95 in any listed era) with a column already kept."""
    order = sorted(cols, key=lambda n: (INP[n]["lookback_bars"], -coverage_of(n), INP[n]["dictionary_position"]))
    kept, dropped = [], {}
    for n in order:
        hits = []
        for k in kept:
            for era, rho in rhos.items():
                v = rho.loc[n, k]
                if np.isfinite(v) and abs(v) > THRESHOLD: hits.append(dict(kept_column=k, era=era, rho=round(float(v), 6)))
        if hits: dropped[n] = hits
        else: kept.append(n)
    return order, kept, dropped


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    state = {}
    stale, seas, rho_tables = {}, {}, {}
    medians_all, yearly_all, problems_434, undefined_all = [], [], [], {}
    for era in ERAS:
        st = prepare_era(era); state[era] = st
        log(f"{era}: 4.3.5 stale closes")
        summary, by_year, by_slot = stale_closes(st); stale[era] = (summary, by_year, by_slot)
        log(f"{era}: 4.3.5 flagged {summary['flagged_bars']} bars in {summary['runs_of_5_or_more']} runs ({summary['share_of_grid_rows_pct']}% of grid rows)")
        log(f"{era}: 4.3.4 seasonality medians and 4.3.6 yearly statistics")
        med_df, y6, problems, undef = seasonality_and_yearly(st)
        problems_434 += [f"{era}: {p}" for p in problems]; undefined_all[era] = undef
        write_csv(f"sec4_3_4_slot_medians_{era}.csv", med_df, f"4.3.4 TRAIN median per slot, {era}")
        yearly_all.append(y6)
        if era == "RAW":
            log("RAW: 4.3.8 Spearman, all 80 columns")
            rho_tables["RAW"] = spearman_matrix(st, NAMES, "RAW 80x80")
        else:
            log("LEGACY: 4.3.8 Spearman, the 20 primary columns")
            rho_tables["LEGACY"] = spearman_matrix(st, PRIMARY, "LEGACY 20x20")
    write_csv("sec4_3_5_stale_closes_by_year.csv", pd.concat([stale[e][1] for e in ERAS]), "4.3.5 flagged bars by era and year")
    write_csv("sec4_3_5_stale_closes_by_slot.csv", pd.concat([stale[e][2] for e in ERAS]), "4.3.5 flagged bars by era and slot")
    write_csv("sec4_3_6_yearly_median_iqr.csv", pd.concat(yearly_all), "4.3.6 yearly median and IQR (80 raw + 36 adjusted columns)")

    # ---- 4.3.7
    log("4.3.7 eligibility")
    step6_pass = [c for c, v in COV.items() if v["status"] == "PASS"]
    elig_checks = {
        "primary set equals the 20 PASS columns of Step 6": sorted(step6_pass) == sorted(PRIMARY),
        "primary set recomputed from this run's coverage (both eras >= 80%, rounded to 3 decimals as in Step 6)": sorted(n for n in NAMES if all(round(100 * state[e]["finite"][n] / state[e]["rows"], 3) >= 80 for e in ERAS)) == sorted(PRIMARY),
        "sensitivity set is all 80 detector outputs": len(NAMES) == 80,
        "overnight_return_open is in neither set": "overnight_return_open" not in NAMES,
    }
    elig = dict(primary=PRIMARY, sensitivity_RAW=NAMES, checks=elig_checks,
                raw_coverage_range_pct=[min(COV[n]["RAW_pct"] for n in NAMES), max(COV[n]["RAW_pct"] for n in NAMES)])
    write("sec4_3_7_eligibility.json", json.dumps(elig, indent=2) + "\n", "4.3.7 eligibility sets")

    # ---- 4.3.8
    log("4.3.8 redundancy")
    rhoR, ovR = rho_tables["RAW"]; rhoL, ovL = rho_tables["LEGACY"]
    rho_primary = {"LEGACY": rhoL, "RAW": rhoR.loc[PRIMARY, PRIMARY]}
    order_p, kept_p, drop_p = redundancy(PRIMARY, rho_primary, lambda n: min(INP[n]["coverage_LEGACY_pct"], INP[n]["coverage_RAW_pct"]))
    order_s, kept_s, drop_s = redundancy(NAMES, {"RAW": rhoR}, lambda n: INP[n]["coverage_RAW_pct"])
    rhoL.to_csv(R / "sec4_3_8_spearman_primary_LEGACY.csv"); OUTPUTS.append(("4.3.8 Spearman, primary set, LEGACY", R / "sec4_3_8_spearman_primary_LEGACY.csv"))
    rhoR.to_csv(R / "sec4_3_8_spearman_RAW_all80.csv"); OUTPUTS.append(("4.3.8 Spearman, all 80, RAW (primary RAW is a sub-block)", R / "sec4_3_8_spearman_RAW_all80.csv"))
    ovR.to_csv(R / "sec4_3_8_overlap_RAW_all80.csv"); OUTPUTS.append(("4.3.8 pairwise overlap counts, RAW", R / "sec4_3_8_overlap_RAW_all80.csv"))
    ovL.to_csv(R / "sec4_3_8_overlap_primary_LEGACY.csv"); OUTPUTS.append(("4.3.8 pairwise overlap counts, LEGACY primary", R / "sec4_3_8_overlap_primary_LEGACY.csv"))
    undefined_pairs = {"RAW": int(np.isnan(rhoR.to_numpy()).sum()), "LEGACY_primary": int(np.isnan(rhoL.to_numpy()).sum())}
    def verify(kept, dropped, rhos, cols):
        ok = True
        for a in kept:
            for b in kept:
                if a != b and any(np.isfinite(r.loc[a, b]) and abs(r.loc[a, b]) > THRESHOLD for r in rhos.values()): ok = False
        for n, hits in dropped.items():
            if not any(h["kept_column"] in kept for h in hits): ok = False
        return ok and len(kept) + len(dropped) == len(cols)
    red = dict(rule=A3["rules"]["4.3.8_redundancy"]["keep_rule"], threshold=THRESHOLD,
               primary=dict(priority_order=order_p, kept=kept_p, dropped=drop_p), sensitivity_RAW=dict(priority_order=order_s, kept=kept_s, dropped=drop_s),
               undefined_correlations=undefined_pairs,
               checks={"primary: no two kept columns redundant, every dropped column has a kept partner": verify(kept_p, drop_p, rho_primary, PRIMARY),
                       "sensitivity: no two kept columns redundant, every dropped column has a kept partner": verify(kept_s, drop_s, {"RAW": rhoR}, NAMES)})
    write("sec4_3_8_redundancy.json", json.dumps(red, indent=2) + "\n", "4.3.8 redundancy outcome")
    log(f"4.3.8 primary: keep {len(kept_p)}, drop {len(drop_p)}; sensitivity (RAW, 80): keep {len(kept_s)}, drop {len(drop_s)}")

    # ---- 4.3.9
    log("4.3.9 frozen matrix")
    rows = []
    for n in NAMES:
        e = DICT[n]
        def outcome(n_, kept, dropped, in_set):
            if not in_set: return "not in set"
            if n_ in kept: return "kept"
            h = dropped[n_][0]
            return f"dropped: redundant with {h['kept_column']} (rho {h['rho']}, {h['era']})"
        rows.append(dict(output=n, feature_class="scale (adjusted version added)" if n in SCALE else "raw only", adjusted_column=(n + "__sadj") if n in SCALE else "",
                         lookback_bars=e["lookback_bars"], lookback_sessions=e["lookback_sessions"], min_valid_obs=e["min_valid_obs"], warmup=e["warmup"],
                         coverage_LEGACY_pct=COV[n]["LEGACY_pct"], coverage_RAW_pct=COV[n]["RAW_pct"],
                         primary_eligible=n in PRIMARY, sensitivity_eligible=True,
                         primary_redundancy=outcome(n, kept_p, drop_p, n in PRIMARY), sensitivity_redundancy=outcome(n, kept_s, drop_s, True),
                         outputs="sec4_3_4_slot_medians_*.csv; sec4_3_5_*; sec4_3_6_yearly_median_iqr.csv; sec4_3_8_*"))
    matrix = pd.DataFrame(rows)
    write_csv("sec4_3_9_frozen_matrix.csv", matrix, "4.3.9 frozen matrix (A3: one matrix, both sets)")
    write_csv("sec4_3_9_matrix_primary_view.csv", matrix[matrix.primary_eligible], "4.3.9 primary view (20 eligible rows)")
    write_csv("sec4_3_9_matrix_sensitivity_view.csv", matrix[["output", "feature_class", "adjusted_column", "lookback_bars", "coverage_RAW_pct", "sensitivity_eligible", "sensitivity_redundancy"]], "4.3.9 sensitivity view (80 rows, RAW)")
    matrix_checks = {"80 rows": len(matrix) == 80, "all A3 matrix fields present": all(c in matrix.columns for c in ["feature_class", "adjusted_column", "lookback_bars", "min_valid_obs", "warmup", "coverage_LEGACY_pct", "coverage_RAW_pct", "primary_eligible", "sensitivity_eligible", "primary_redundancy", "sensitivity_redundancy"]),
                     "36 adjusted columns named": int((matrix.adjusted_column != "").sum()) == len(SCALE),
                     "A3 hash verified": True}

    # ---- report
    flagged = {e: stale[e][0] for e in ERAS}
    y6 = pd.concat(yearly_all)
    sub = {
        "4.3.2/4.3.3": dict(status="CITED, NO WORK", cites={"A2": sha(one("amendment_4_3_1_A2_*.json")), "P1": sha(one("policy_4_3_1_P1_2*.json")), "prior 4.3.2/4.3.3 synthetic audit": A3["timing"]["prior_run_found_4_3_2_4_3_3"]["sha256"]}),
        "4.3.4": dict(status="PASS" if not problems_434 else "FAIL", checks=dict(adjusted_columns=len(SCALE), problems=problems_434,
                      slots_with_undefined_median_per_feature={e: {k: v for k, v in undefined_all[e].items() if v} for e in ERAS})),
        "4.3.5": dict(status="DESCRIPTIVE", result=flagged),
        "4.3.6": dict(status="DESCRIPTIVE", rows=int(len(y6)), columns=80 + len(SCALE), eras_years={e: sorted(y6[y6.era == e].year.unique().tolist()) for e in ERAS}),
        "4.3.7": dict(status="PASS" if all(elig_checks.values()) else "FAIL", checks=elig_checks, primary_count=len(PRIMARY), sensitivity_count=len(NAMES)),
        "4.3.8": dict(status="PASS" if all(red["checks"].values()) else "FAIL", checks=red["checks"],
                      primary=dict(kept=len(kept_p), dropped=len(drop_p)), sensitivity_RAW=dict(kept=len(kept_s), dropped=len(drop_s)), undefined_correlations=undefined_pairs),
        "4.3.9": dict(status="PASS" if all(matrix_checks.values()) else "FAIL", checks=matrix_checks),
    }
    now = datetime.datetime.now(datetime.timezone.utc)
    hashes = [dict(label=l, file=p.name, sha256=sha(p)) for l, p in OUTPUTS]
    report = dict(created_utc=now.isoformat(), amendment_A3=dict(file=A3_FILE.name, sha256=sha(A3_FILE)), scope="TRAIN only; RAW then LEGACY; 80 detector outputs; overnight_return_open excluded",
                  readings_stated=["4.3.5 shares are given against both all TRAIN grid rows and observed bars (A3 does not name the denominator).",
                                   "4.3.9: A3 specifies one matrix holding both sets; the primary and sensitivity matrices are views of it."],
                  subsections=sub, overall=("PASS" if all(v["status"] in ("PASS", "DESCRIPTIVE", "CITED, NO WORK") for v in sub.values()) else "FAIL"),
                  output_hashes=hashes)
    rp = R / "sec4_3_4_to_4_3_9_report.json"
    rp.write_bytes((json.dumps(report, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n").encode("utf-8"))
    L = ["# Sections 4.3.4-4.3.9 (amendment A3)", "", f"Run {now.isoformat()} UTC. A3 `{A3_FILE.name}` SHA-256 `{sha(A3_FILE)}`. TRAIN only, RAW then LEGACY.", "",
         "| Section | Status | Result |", "|---|---|---|",
         "| 4.3.2/4.3.3 | CITED, NO WORK | A2, P1 and the 2026-10-29 synthetic audit are cited by hash |",
         f"| 4.3.4 Seasonality | {sub['4.3.4']['status']} | {len(SCALE)} adjusted columns; per-slot median of every adjusted column equals 1 |",
         f"| 4.3.5 Stale closes | DESCRIPTIVE | RAW {flagged['RAW']['flagged_bars']} flagged bars ({flagged['RAW']['share_of_grid_rows_pct']}% of grid rows, {flagged['RAW']['share_of_observed_bars_pct']}% of observed); LEGACY {flagged['LEGACY']['flagged_bars']} ({flagged['LEGACY']['share_of_grid_rows_pct']}%, {flagged['LEGACY']['share_of_observed_bars_pct']}%) |",
         f"| 4.3.6 Yearly median/IQR | DESCRIPTIVE | {len(y6)} rows: {80 + len(SCALE)} columns by era and year |",
         f"| 4.3.7 Eligibility | {sub['4.3.7']['status']} | primary {len(PRIMARY)} columns; sensitivity 80 on RAW |",
         f"| 4.3.8 Redundancy | {sub['4.3.8']['status']} | primary keep {len(kept_p)}, drop {len(drop_p)}; sensitivity (RAW) keep {len(kept_s)}, drop {len(drop_s)} |",
         f"| 4.3.9 Frozen matrix | {sub['4.3.9']['status']} | 80 rows, primary and sensitivity views |", "",
         f"Overall: **{report['overall']}**", "", "## Readings stated", ""] + [f"- {t}" for t in report["readings_stated"]]
    L += ["", "## Primary set: kept", "", ", ".join(kept_p), "", "## Primary set: dropped", ""] + [f"- {n}: redundant with {h[0]['kept_column']} (rho {h[0]['rho']}, {h[0]['era']})" for n, h in drop_p.items()]
    L += ["", "## Sensitivity set (RAW, all 80): kept", "", ", ".join(kept_s), "", f"Dropped: {len(drop_s)} columns (see sec4_3_8_redundancy.json).", "",
          "## Output hashes (SHA-256)", "", "| Output | File | SHA-256 |", "|---|---|---|"] + [f"| {h['label']} | {h['file']} | `{h['sha256']}` |" for h in hashes]
    mp = R / "sec4_3_4_to_4_3_9_report.md"
    mp.write_text("\n".join(L) + "\n", encoding="utf-8")
    (R / "sec4_3_4_to_4_3_9_report.sha256").write_text(f"{sha(rp)}  {rp.name}\n{sha(mp)}  {mp.name}\n", encoding="ascii")
    shutil.rmtree(TMP, ignore_errors=True)
    log("done")
    print("\n".join(L[:20]))
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
