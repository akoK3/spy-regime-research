#!/usr/bin/env python3
"""Write amendment A3: the rules for Sections 4.3.2-4.3.9, dated and hashed before 4.3.4-4.3.9 are run.
Reads only saved documents and result files; runs no analysis and reads no market data. Refuses to overwrite."""
import json, hashlib, subprocess, datetime, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
R = ROOT / "section431_step3_all_in_one_results"
FZ = ROOT / "frozen_documents"
PRIOR_AUDIT = Path(r"C:\Users\kakij\OneDrive\Desktop\data\section4_3_rebuild_20261028\audit_4_3_2_4_3_3_report.json")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def one(pattern):
    files = sorted(R.glob(pattern))
    assert len(files) == 1, pattern
    return files[0]


def is_scale(n):
    return bool(re.match(r"(rv\d+_(strict|partial90)|downside\d+_(strict|partial90)|rv60_sampled5_exact|abs_return_1m|intrabar_range_log|raw_volume|relative_volume20|"
                         r"(amihud|bipower|jump_variation|vol_of_vol|volume_adjusted_range)_\d+)$", n))


def main():
    assert not list(R.glob("amendment_4_3_A3_2*.json")), "A3 exists; never overwrite"
    closing_f = one("section_4_3_1_closing_report_2*.json")
    closing, cov = json.loads(closing_f.read_text(encoding="utf-8")), json.loads((R / "step6_coverage_TRAIN.json").read_text(encoding="utf-8"))
    dictionary = [x for x in closing["feature_dictionary"] if x["role"] == "detector"]
    names = [x["output"] for x in dictionary]
    assert len(names) == 80
    scale = [n for n in names if is_scale(n)]
    raw_only = [n for n in names if not is_scale(n)]
    primary = [c["column"] for c in cov["columns"] if c["status"] == "PASS"]
    assert len(scale) + len(raw_only) == 80 and len(primary) == 20 and cov["counts"] == {"PASS": 20, "BELOW": 60}
    ns, nr = len(scale), len(raw_only)

    cited = {
        "amendment_A2 (4.3.1-A2)": one("amendment_4_3_1_A2_*.json"),
        "policy_P1": one("policy_4_3_1_P1_2*.json"),
        "policy_P1_addendum": one("policy_4_3_1_P1_addendum_2*.json"),
        "policy_P1_verification_v2": one("policy_4_3_1_P1_verification_v2_*.json"),
        "approval_of_4.3.0-A1": one("approval_4_3_0_A1_2*.json"),
        "section_4_3_1_closing_report": closing_f,
        "step6_coverage_TRAIN": R / "step6_coverage_TRAIN.json",
        "step4_parameter_table": R / "step4_parameter_table.json",
        "frozen_protocol_v2": FZ / "protocol_20261029T032641Z.json",
        "coverage_amendment_4.3.1-A2-post-screening": FZ / "protocol_amendment_431_A2_FROZEN_coverage.json",
        "amendment_4.3.0-A1": FZ / "protocol_amendment_4_3_0_A1_20261029T034121Z.json",
    }
    now = datetime.datetime.now(datetime.timezone.utc)
    doc = {
        "amendment": "4.3.2-4.3.9-A3",
        "created_utc": now.isoformat(),
        "created_america_new_york": pd.Timestamp(now).tz_convert("America/New_York").isoformat(),
        "status": "RULES_FIXED_BEFORE_SECTIONS_4_3_4_TO_4_3_9_ARE_RUN",
        "timing": {
            "statement": "These rules are fixed before any analysis of Sections 4.3.4-4.3.9 is run. No file for those sections was found in the repository, in Downloads or in the data folder when this was written. No rule may be changed after a run has seen the data; a change needs a new dated amendment (A4).",
            "prior_run_found_4_3_2_4_3_3": {"file": PRIOR_AUDIT.name, "sha256": sha(PRIOR_AUDIT), "scope": "source-level synthetic tests, 12 tests, status PASS_SYNTHETIC, 2026-10-29",
                                           "deferred_in_that_audit": ["Historical source timestamp labeling and vendor causality", "Full-data construction/output validation on user machine", "Decision-time joins of completed-bar features", "Section 5 event-label horizons and purging", "Training-only normalization and fitted model enforcement"],
                                           "effect": "Stands as it is; A3 adds no work to 4.3.2/4.3.3."},
            "earlier_related_work": "Results for seasonality (section 4.4), normalization (4.6) and redundancy (4.7) exist from the pre-rebuild pipeline on the earlier feature set, and that pipeline used the 2025-2026 period (see REPORT.md exposure audit). These rules were written with that work possibly known and are not blind to it. They use only the frozen TRAIN spans.",
        },
        "cites": {k: {"file": p.name, "sha256": sha(p)} for k, p in cited.items()},
        "general_rules": [
            "TRAIN rows only (LEGACY 2003-01-02..2018-12-21, RAW 2022-03-07..2024-12-23); no evaluation data.",
            "Eras are computed separately; no value, statistic or window crosses the LEGACY/RAW boundary (P1 R3).",
            "The 80 detector outputs of A2 are the only columns; overnight_return_open is excluded everywhere.",
            "No formula, threshold or classification already frozen is changed. Only 4.3.7 and 4.3.8 produce decisions; 4.3.4-4.3.6 are descriptive and exclude nothing.",
            "Every output file is hashed (SHA-256 sidecar) when written and never edited afterwards.",
        ],
        "rules": {
            "4.3.2_4.3.3": "Cite A2 and P1. No new work.",
            "4.3.4_seasonality": {
                "keep_raw": "Every raw column is kept unchanged.",
                "adjusted_version": "For each scale feature add <name>__sadj = raw value / TRAIN median of that raw column at the same minute of the session, computed per era.",
                "minute_of_session": "the slot index counted from the 09:30 open; early-close sessions populate slots 0-209 only.",
                "median": "median of the finite TRAIN values of the raw column at that slot in that era; the adjusted value is NaN where there is no finite median or the median is <= 0.",
                "median_table": "the per-era, per-slot, per-feature median table is saved and hashed.",
                "scale_features": f"positive-valued magnitudes of volatility, volume, range or Amihud illiquidity ({ns} columns, listed in feature_classes).",
                "signed_features": f"signed, bounded, shape, flag and log-transformed columns stay raw only ({nr} columns, listed in feature_classes). log_raw_volume and log_relative_volume20 are raw only; raw_volume and relative_volume20 carry the volume adjustment.",
                "inherited_constraint": "The TRAIN median is a fixed per-era statistic for this descriptive step. The frozen protocol requires fold fit statistics to use training rows only, so any use of an adjusted column inside nested folds recomputes the medians on each fold's training rows.",
            },
            "4.3.5_stale_prices": {
                "cites": "Step 2 (missingness and calendar audit) and Step 6 (coverage).",
                "flag": "A run is 5 or more consecutive grid bars within a session whose Close values are finite and exactly equal; a missing bar ends a run. Every bar of such a run is flagged.",
                "output": "counts and shares of flagged bars by era, by year and by slot. Descriptive only: no value is altered or removed.",
            },
            "4.3.6_yearly_distribution": {
                "statistic": f"per calendar year and era, the median and the interquartile range (Q3 - Q1, linear interpolation) of each of the 80 raw columns and of the {ns} adjusted columns, over finite TRAIN values.",
                "output": "descriptive; no exclusions.",
            },
            "4.3.7_eligibility": {
                "primary": "columns with at least 80% coverage in both eras: the 20 columns that are PASS in Step 6 (listed in eligibility_sets, from the hashed step6_coverage_TRAIN.json).",
                "sensitivity": "all 80 detector outputs, on RAW only.",
                "adjusted_columns": "an adjusted column follows the eligibility of its raw column and is not a separate candidate.",
                "excluded": "overnight_return_open in both sets.",
            },
            "4.3.8_redundancy": {
                "statistic": "Spearman correlation on TRAIN rows, pairwise-complete, per era; the overlap counts are reported. A pair is redundant if |rho| > 0.95 in either era. In the sensitivity set only RAW exists, so only RAW is used. An undefined correlation does not make a pair redundant and is reported.",
                "applies_to": "raw columns of each eligibility set separately.",
                "keep_rule": "Process the columns in priority order and keep a column unless it is redundant with a column already kept. Priority: (1) shorter window, meaning the smaller Step 4 lookback in bars; (2) higher coverage, meaning the lower of the two eras' Step 6 coverage in the primary set and the RAW coverage in the sensitivity set; (3) earlier position in the closing-report feature dictionary. Rule (3) is a deterministic tie-break added here and is not part of the instruction as first given.",
                "output": "for every dropped column, the kept column it was redundant with, the correlation and the era.",
            },
            "4.3.9_frozen_matrix": {
                "content": "one matrix with a row per detector column: class (scale or raw only), adjusted-column name, lookback, minimum valid observations, warmup, LEGACY and RAW coverage, primary and sensitivity eligibility, redundancy outcome in each set, and pointers to the 4.3.4-4.3.8 outputs.",
                "hashes": "SHA-256 of the matrix and of every 4.3.4-4.3.8 output, together with the hashes of A1 (approval), A2, A3, P1 and the closing report.",
                "freeze": "Written once and never edited; any change needs a new dated amendment. No data files are included.",
            },
        },
        "feature_classes": {"scale_adjusted": scale, "raw_only": raw_only},
        "eligibility_sets": {"primary_20": primary, "sensitivity": "all 80 detector outputs, RAW only"},
        "redundancy_priority_inputs": [{"output": x["output"], "lookback_bars": x["lookback_bars"], "coverage_LEGACY_pct": x["coverage_LEGACY_pct"], "coverage_RAW_pct": x["coverage_RAW_pct"], "dictionary_position": i}
                                       for i, x in enumerate(dictionary)],
        "not_decided_here": ["Which of the 60 below-floor columns are used later", "The overnight analysis", "Any detector, scaler or HMM fit"],
    }
    path = R / f"amendment_4_3_A3_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    data = (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    path.with_suffix(".sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    print(path.name, "\nSHA-256:", digest, "\ncreated_utc:", doc["created_utc"], "| scale:", len(scale), "| raw only:", len(raw_only), "| primary:", len(primary))


if __name__ == "__main__":
    main()
