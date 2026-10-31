#!/usr/bin/env python3
"""Write the Section 4 closing report. Scope: Section 4.3 (4.3.0-4.3.9) as recorded in this repository.
Reads saved results only; reruns nothing; refuses to overwrite."""
import json, hashlib, subprocess, datetime
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
R = ROOT / "section431_step3_all_in_one_results"
FZ = ROOT / "frozen_documents"
REPORT_MD = Path(r"C:\Users\kakij\OneDrive\Desktop\data\section4_3_rebuild_20261028\REPORT.md")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def one(pattern, base=R):
    files = sorted(base.glob(pattern))
    assert len(files) == 1, pattern
    return files[0]


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    assert not list(R.glob("section_4_3_closing_report_section4_2*.json")), "exists; never overwrite"
    rep, red, follow = load(R / "sec4_3_4_to_4_3_9_report.json"), load(R / "sec4_3_8_redundancy.json"), load(R / "sec4_3_5b_legacy_stale_zero_volume.json")
    prior = one("section_4_3_1_closing_report_2*.json")
    note, a3 = one("note_4_3_N1_2*.json"), one("amendment_4_3_A3_2*.json")
    sub = rep["subsections"]
    assert rep["overall"] == "PASS" and follow["total"]["stale_bars_zero_volume"] == 0
    documents = [
        ("Frozen protocol v2 (4.3.0 splits, clocks; 35 features)", FZ / "protocol_20261029T032641Z.json"),
        ("Frozen protocol v1 (superseded)", FZ / "protocol_20261029T032504Z.json"),
        ("Amendment 4.3.0-A1 (approved after use)", FZ / "protocol_amendment_4_3_0_A1_20261029T034121Z.json"),
        ("Approval of 4.3.0-A1", one("approval_4_3_0_A1_2*.json")),
        ("Coverage amendment 4.3.1-A2-post-screening", FZ / "protocol_amendment_431_A2_FROZEN_coverage.json"),
        ("Amendment 4.3.1-A2 (45 outputs, cap, overnight exclusion)", one("amendment_4_3_1_A2_*.json")),
        ("Policy 4.3.1-P1", one("policy_4_3_1_P1_2*.json")),
        ("Policy addendum 4.3.1-P1-A", one("policy_4_3_1_P1_addendum_2*.json")),
        ("Amendment 4.3.2-4.3.9-A3", a3),
        ("Note 4.3-N1 (candidate pool; overnight response-side only)", note),
        ("Section 4.3.1 closing report", prior),
        ("Sections 4.3.4-4.3.9 report", R / "sec4_3_4_to_4_3_9_report.json"),
        ("4.3.8 redundancy outcome", R / "sec4_3_8_redundancy.json"),
        ("4.3.9 frozen matrix", R / "sec4_3_9_frozen_matrix.csv"),
        ("4.3.5b LEGACY stale runs and zero volume", R / "sec4_3_5b_legacy_stale_zero_volume.json"),
        ("REPORT.md (Section 4.3.0 exposure audit and original 4.3.1 construction)", REPORT_MD),
    ]
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    inventory = [dict(path=p, sha256=sha(ROOT / p)) for p in tracked]
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    pool = 80 + 36
    t = follow["total"]
    steps = [
        ("4.3.0", "Splits, exposure audit, provider and clock rules", "Frozen protocol v2 (hash below). Development: LEGACY 2003-01-02..2022-03-04 (4,827 sessions), RAW 2022-03-07..2024-12-31 (710). 2025-01-02..2026-10-12 is exposed retrospective evaluation, not an untouched test; no unexposed period exists. 40 nested folds (36 LEGACY, 4 RAW). Amendment 4.3.0-A1 is approved, after 4.3.1 had used it. Source: REPORT.md."),
        ("4.3.1", "35 frozen candidates plus 45 specified outputs", "Closed in the 4.3.1 closing report (hash below): 81 outputs audited in both eras (PASS), 80 detector outputs match the frozen protocol and A2, overnight_return_open excluded, policy P1 verified, coverage 20 PASS / 60 BELOW in LEGACY."),
        ("4.3.2/4.3.3", "Cited, no new work", "A2, P1 and the 2026-10-29 synthetic audit (12 tests, PASS_SYNTHETIC) stand."),
        ("4.3.4", "Seasonality", f"{sub['4.3.4']['status']}: 36 adjusted columns (feature / TRAIN median at that minute, per era); per-slot median of each adjusted column is 1; no slot had an undefined median."),
        ("4.3.5", "Stale closes (5+ identical closes)", f"Descriptive: RAW {sub['4.3.5']['result']['RAW']['flagged_bars']} bars; LEGACY {sub['4.3.5']['result']['LEGACY']['flagged_bars']} bars ({sub['4.3.5']['result']['LEGACY']['share_of_grid_rows_pct']}% of grid rows) in {t['stale_runs']} runs. Follow-up (post-hoc, not in A3): {t['stale_bars_zero_volume']} of those bars have zero volume in every year, and LEGACY has no zero-volume bar at all ({t['context_all_observed_bars_zero_volume_pct']}% of observed bars), so the repeated closes carry volume."),
        ("4.3.6", "Yearly median/IQR", f"Descriptive: {sub['4.3.6']['rows']} rows for {sub['4.3.6']['columns']} columns by era and year; nothing excluded."),
        ("4.3.7", "Eligibility", f"{sub['4.3.7']['status']}: primary = 20 columns (80% in both eras, = Step 6 PASS); sensitivity = all 80 on RAW; overnight in neither."),
        ("4.3.8", "Redundancy (|Spearman| > 0.95)", f"{sub['4.3.8']['status']}: primary keep {sub['4.3.8']['primary']['kept']} / drop {sub['4.3.8']['primary']['dropped']}; sensitivity (RAW) keep {sub['4.3.8']['sensitivity_RAW']['kept']} / drop {sub['4.3.8']['sensitivity_RAW']['dropped']}; no undefined correlations."),
        ("4.3.9", "Frozen matrix", f"{sub['4.3.9']['status']}: 80 rows with primary and sensitivity views; every output hashed."),
        ("Pool", "Candidate pool and overnight (note 4.3-N1)", f"Adjusted columns join the pool alongside raw ({pool} columns); overnight_return_open is response-side only. Redundancy for the {pool}-column pool was not computed."),
    ]
    limitations = [
        "Scope: this report closes Section 4.3 (4.3.0-4.3.9) as recorded here. Results of the pre-rebuild pipeline (sections 4.4-4.9 and the older 4.3 runs) are not part of this record, and A3 and N1 were written with those results possibly known.",
        "60 of the 80 detector outputs remain below the 80% coverage floor in LEGACY. The sensitivity analysis uses them on RAW only; LEGACY has no sensitivity analysis. Which to keep is undecided.",
        "LEGACY has 3,977 runs of 5 or more identical closes (1.48% of grid rows) and RAW has 5 bars. The cause is not established; no value was excluded or changed. The run definition is exact equality of finite closes within a session.",
        "4.3.4 PASS verifies the adjustment mechanics (per-slot median 1), not that the adjustment is useful. The TRAIN medians are fixed per era, not point-in-time; any use inside nested folds must recompute them on each fold's training rows.",
        "4.3.8 uses Spearman on pooled TRAIN rows with pairwise-complete overlap (re-ranked per pair). The priority rule picks by window then coverage, not by the value of a feature. Raw/adjusted redundancy was not computed (N1).",
        "Two readings were stated, not resolved by the amendment: 4.3.5 shares are given against both denominators, and the 4.3.9 'primary and sensitivity matrices' are views of A3's single matrix. N1 changes two A3 sentences and was written after the run.",
        "Everything is TRAIN-only (LEGACY to 2018-12-21, RAW to 2024-12-23). The frozen development days after those dates, the boundary days around 2022-03-04/07 and the evaluation period were never in an audited or analysed span.",
        "The 4.3.1 closing report's limitations remain in force: synthetic-panel formula checks, 40-session slice tests, post-hoc A2 specification, return-bar cap definition, unresolved A1 conflicts (60-minute lookback, 5-session embargo vs 20-session relative volume), declarative overnight exclusion, unresolved LEGACY clock semantics.",
        "The follow-up in 4.3.5b was run on request after the A3 run and is not defined by A3; it is descriptive only.",
    ]
    deferred = ["Which below-floor outputs to keep, drop or re-window", "Redundancy and eligibility rules for the 116-column pool", "The overnight analysis (response side) and its specification",
                "Reconciling A1's 60-minute lookback and 5-session embargo with A2/A3", "Any detector, scaler or HMM fit", "Legacy timing sensitivity (-1/0/+1 minute)"]
    now = datetime.datetime.now(datetime.timezone.utc)
    ny = pd.Timestamp(now).tz_convert("America/New_York").isoformat()
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    report = dict(status="SECTION_4_3_CLOSED", scope="Section 4.3 (4.3.0-4.3.9) as recorded in this repository", closed_utc=now.isoformat(), closed_america_new_york=ny,
                  repo_head_before_closing_commit=head, steps=[dict(section=a, title=b, result=c) for a, b, c in steps],
                  primary_kept=red["primary"]["kept"], primary_dropped={k: v[0] for k, v in red["primary"]["dropped"].items()},
                  sensitivity_RAW_kept=red["sensitivity_RAW"]["kept"], sensitivity_RAW_dropped=len(red["sensitivity_RAW"]["dropped"]),
                  stale_zero_volume=t, documents=[dict(name=n, file=p.name, sha256=sha(p)) for n, p in documents], file_inventory=inventory,
                  known_limitations=limitations, decisions_not_taken=deferred)
    jp = R / f"section_4_3_closing_report_section4_{stamp}.json"
    jp.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    L = ["# Section 4 closing report", "", "**SECTION_4_3_CLOSED**", "",
         f"Closed {now.isoformat()} UTC ({ny} New York). Repository HEAD before this commit: `{head}`.", "",
         "Scope: Section 4.3 (4.3.0-4.3.9) as recorded in this repository. Closed means the construction, audit and the A3 analyses are complete and recorded; the open decisions below are not settled.", "",
         "## Results by subsection", "", "| Section | Scope | Result |", "|---|---|---|"] + [f"| {a} | {b} | {c} |" for a, b, c in steps]
    L += ["", "## Frozen matrices", "",
          f"Primary set (20 columns) kept {len(red['primary']['kept'])}: {', '.join(red['primary']['kept'])}.", "",
          "Primary set dropped: " + "; ".join(f"{k} (redundant with {v[0]['kept_column']}, rho {v[0]['rho']}, {v[0]['era']})" for k, v in red["primary"]["dropped"].items()) + ".", "",
          f"Sensitivity set (all 80, RAW) kept {len(red['sensitivity_RAW']['kept'])}, dropped {len(red['sensitivity_RAW']['dropped'])}; the full lists and the matrix are in `sec4_3_8_redundancy.json` and `sec4_3_9_frozen_matrix.csv`.", "",
          "## LEGACY stale runs by year: zero-volume share", "", "| Year | Stale bars | Zero-volume stale bars | Runs | Runs with any zero volume |", "|---|---|---|---|---|"]
    fy = pd.read_csv(R / follow["by_year_file"])
    L += [f"| {r.year} | {r.stale_bars} | {r.stale_bars_zero_volume} ({r.stale_bars_zero_volume_pct}%) | {r.stale_runs} | {r.runs_any_zero_volume} |" for r in fy.itertuples()]
    L += ["", "## Amendments, policies, notes and key results (SHA-256)", "", "| Document | File | SHA-256 |", "|---|---|---|"] + [f"| {n} | {p.name} | `{sha(p)}` |" for n, p in documents]
    L += ["", "## Known limitations", ""] + [f"{i}. {x}" for i, x in enumerate(limitations, 1)]
    L += ["", "## Decisions not taken", ""] + [f"- {x}" for x in deferred]
    L += ["", "## SHA-256 inventory of tracked files (before the closing commit)", "", "| Path | SHA-256 |", "|---|---|"] + [f"| {x['path']} | `{x['sha256']}` |" for x in inventory]
    mp = jp.with_suffix(".md")
    mp.write_text("\n".join(L) + "\n", encoding="utf-8")
    jp.with_name(jp.stem + ".sha256").write_text(f"{sha(jp)}  {jp.name}\n{sha(mp)}  {mp.name}\n", encoding="ascii")
    print(jp.name); print((jp.with_name(jp.stem + ".sha256")).read_text())


if __name__ == "__main__":
    main()
