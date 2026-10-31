"""Audit existing evidence, finalize historical boundaries, freeze Section 4.3.0.

This does not rerun old experiments or select dates using their scores.
It reads prior result metadata and availability flags, snapshots evidence,
and writes a new protocol. Never overwrites an existing freeze.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from section4_3_1_candidates import WINDOWS, construct, sha256
from test_candidates import sample

ROOT = Path(__file__).resolve().parent
DOWNLOADS = Path.home()/"Downloads"


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")


def main():
    if list(ROOT.glob("protocol_*Z.json")):
        raise SystemExit("A frozen protocol already exists. Create a versioned directory for amendments.")
    evidence = ROOT/"evidence"
    evidence.mkdir(exist_ok=True)
    relpaths = [
        "section4_3_0_split_protocol_DRAFT.json",
        "section4_8C_feature_validation.py", "section4_8D_frequency_and_stability.py",
        "section4_8_feature_selection_stage2.py", "section4_8_feature_selection_stage1_v2.py",
        "section4_7_feature_redundancy.py",
        "section4_8C_feature_validation_results/summary.json",
        "section4_8C_feature_validation_results/candidate_scores.csv",
        "section4_8C_feature_validation_results/feature_coverage.csv",
        "section4_8D_frequency_results/summary.json",
        "section4_8D_frequency_results/fit_diagnostics.csv",
        "section4_8D_frequency_results/common_support.csv",
        "section4_8C_previous_tick_60m_results/summary.json",
        "section4_8C_previous_tick_60m_results/coverage_by_year.csv",
        "section4_8_feature_selection_stage1_results/nested_fold_boundaries.csv",
        "section4_8_feature_selection_stage2_results/nested_fold_boundaries.csv",
        "section4_7_feature_redundancy_results/chronological_folds.csv",
        "section4_7_feature_redundancy_results/REPORT.md",
        "section4_3_feature_feasibility_results/summary.json",
        "section3_final_closeout_results/MODEL_HANDOFF_CONTRACT.md",
        "section3_final_closeout_results/preprocessing_config.json",
        "section3_final_closeout_results/summary.json",
    ]
    inventory = []
    for rel in relpaths:
        source, dest = DOWNLOADS/rel, evidence/rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        original_hash = sha256(source)
        shutil.copyfile(source, dest)
        assert sha256(dest) == original_hash
        inventory.append(dict(source_file=str(source), snapshot_file=str(dest.relative_to(ROOT)),
                              bytes=source.stat().st_size, sha256=original_hash))
    pd.DataFrame(inventory).to_csv(ROOT/"evidence_inventory.csv", index=False)
    csummary = json.loads((evidence/"section4_8C_feature_validation_results/summary.json").read_text())
    dsummary = json.loads((evidence/"section4_8D_frequency_results/summary.json").read_text())
    # Metadata-only inspection of complete panels, without target returns.
    meta, source_specs, era_inventory, asset_availability = {}, {}, [], []
    for era in ["LEGACY", "RAW"]:
        src = csummary["sources"][era]
        panel, etf = Path(src["panel_file"]), Path(src["etf_file"])
        assert sha256(panel) == src["panel_sha256"]
        assert sha256(etf) == src["etf_sha256"]
        assert dsummary["sources"][era]["panel_sha256"] == src["panel_sha256"]
        assert dsummary["sources"][era]["etf_sha256"] == src["etf_sha256"]
        h = pd.read_csv(panel, nrows=0).columns
        cols = ["session_date_ny", "minute_index_in_session", "source_epoch"]
        cols += [x for x in h if x.endswith("_return_eligible")]
        m = pd.read_csv(panel, usecols=cols)
        assert m.source_epoch.eq(era).all()
        days = m.session_date_ny.drop_duplicates().to_numpy(str)
        meta[era] = dict(frame=m, days=days)
        first, last = (("2003-01-02", "2022-03-04") if era == "LEGACY"
                       else ("2022-03-07", "2024-12-31"))
        mask = m.session_date_ny.between(first, last)
        source_specs[era] = dict(first_session=first, last_session=last,
            calendar_start_inclusive="2003-01-01" if era == "LEGACY" else first,
            calendar_end_inclusive=last, sessions=int(m.loc[mask,"session_date_ny"].nunique()),
            calendar_minutes=int(mask.sum()), panel_file=str(panel), etf_file=str(etf),
            panel_sha256=src["panel_sha256"], etf_sha256=src["etf_sha256"])
        era_inventory.append(dict(era=era, first_panel_session=days[0], last_panel_session=days[-1],
                                  panel_sessions=len(days), panel_minutes=len(m), **source_specs[era]))
        for col in cols:
            if col.endswith("_return_eligible"):
                v = m.loc[m[col].eq(1), "session_date_ny"]
                asset_availability.append(dict(era=era, eligibility_column=col,
                    eligible_minutes=len(v), first_eligible_session=v.min(), last_eligible_session=v.max()))
    pd.DataFrame(era_inventory).to_csv(ROOT/"era_inventory.csv", index=False)
    pd.DataFrame(asset_availability).to_csv(ROOT/"asset_availability_metadata.csv", index=False)

    prior_windows, prior_sessions = [], []
    for experiment, summary in [("4.8C", csummary), ("4.8D", dsummary)]:
        for era in ["LEGACY", "RAW"]:
            days = meta[era]["days"]
            for fold in summary["sources"][era]["fold_ids"]:
                start = fold*126
                tr = days[np.arange(start, start+189, 3)]
                va = days[np.arange(start+189, start+252, 2)]
                prior_windows.append(dict(experiment=experiment, era=era, fold=fold,
                    nominal_train_first=days[start], nominal_train_last=days[start+188],
                    nominal_validation_first=days[start+189], nominal_validation_last=days[start+251],
                    sampled_train_first=tr[0], sampled_train_last=tr[-1], sampled_train_sessions=len(tr),
                    sampled_validation_first=va[0], sampled_validation_last=va[-1], sampled_validation_sessions=len(va),
                    overlaps_proposed_2025_2026_holdout=bool(np.any((np.r_[tr,va] >= "2025-01-01") & (np.r_[tr,va] <= "2026-10-12")))))
                for role, dates in [("train",tr), ("validation",va)]:
                    prior_sessions.extend(dict(experiment=experiment, era=era, fold=fold, role=role,
                                               session_date_ny=day) for day in dates)
    pd.DataFrame(prior_windows).to_csv(ROOT/"prior_fold_windows.csv", index=False)
    pd.DataFrame(prior_sessions).to_csv(ROOT/"prior_exposure_sessions.csv", index=False)
    cscores = pd.read_csv(evidence/"section4_8C_feature_validation_results/candidate_scores.csv")
    dscores = pd.read_csv(evidence/"section4_8D_frequency_results/fit_diagnostics.csv")
    c6, d6 = cscores.query("era == 'RAW' and fold == 6"), dscores.query("era == 'RAW' and fold == 6")
    assert len(c6) and len(d6)
    assert c6.first_valid_date.min() == "2025-12-10" and c6.last_valid_date.max() == "2026-03-12"
    assert c6.status.eq("OK").all()
    exposure = dict(
        finding="2025-2026 is exposed retrospective evaluation, not an untouched final holdout",
        c_raw_fold6_fit_rows=len(c6), c_raw_fold6_state_counts=sorted(c6.states.unique().tolist()),
        d_raw_fold6_fit_rows=len(d6), d_raw_fold6_state_counts=sorted(d6.states.unique().tolist()),
        nominal_training_window=["2025-03-12", "2025-12-09"],
        nominal_validation_window=["2025-12-10", "2026-03-12"],
        direct_score_evidence="4.8C candidate_scores.csv; 4.8D fit_diagnostics.csv and source/code-matched fold reconstruction",
        broader_exposure=["4.8C feature coverage and synthetic RV diagnostics used complete provider eras",
                          "4.8D constructed return series/anchor labels on complete eras before fold scoring",
                          "4.7 holdout feature correlations include 2025-2026",
                          "4.8A/B RAW fold 6 inner selection also overlaps the proposed holdout",
                          "Previous-tick 60m study included TLT/HYG across complete eras; it was not an event-reaction test"],
        summary_metadata_issue="4.8C summary model_inputs.states is scalar 4, but saved score rows contain 2,3,4. Prefer row evidence.",
        limits=["Presence on disk establishes computational exposure; it cannot establish exactly what the researcher remembered or used.",
                "No downstream event-study predictive effect is inferred from availability diagnostics.",
                "Existing outer-unopened flags concern local fold usage; they do not certify a globally unexposed date period.",
                "Legacy outer dates recur in later rolling training windows. Do not label all rolling outer dates globally virgin.",
                "The V1 exposure mentioned in the draft is not independently reconstructed here; no clean-date claim relies on its absence."])
    dump(ROOT/"exposure_audit.json", exposure)

    # Final development folds are generated from calendar sessions only.
    folds = []
    fragments = []
    for era, spec in source_specs.items():
        days = meta[era]["days"]
        days = days[(days >= spec["first_session"]) & (days <= spec["last_session"])]
        for k, outer_start in enumerate(range(252, len(days), 126)):
            outer_end = min(outer_start+126, len(days))
            if outer_end-outer_start < 63:
                fragments.append(dict(era=era, first_session=days[outer_start], last_session=days[-1],
                                      sessions=outer_end-outer_start, action="excluded_terminal_outer_fragment"))
                continue
            a = outer_start-252
            folds.append(dict(era=era, fold=k, inner_train_first=days[a], inner_train_last=days[a+188],
                inner_validation_first=days[a+189], inner_validation_last=days[outer_start-1],
                outer_development_first=days[outer_start], outer_development_last=days[outer_end-1],
                inner_train_sessions=189, inner_validation_sessions=63, outer_sessions=outer_end-outer_start))
    pd.DataFrame(folds).to_csv(ROOT/"development_nested_folds.csv", index=False)
    dump(ROOT/"development_terminal_fragments.json", fragments)
    registry = sorted(construct(sample((210,)))[0])
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    frozen = ROOT/f"protocol_{stamp}.json"
    protocol = dict(
        protocol_id=f"section4_3_0_v1_{stamp}", status="FROZEN_RETROSPECTIVE_EXPLORATORY",
        frozen_utc=now.isoformat(), frozen_america_new_york=now.astimezone(ZoneInfo("America/New_York")).isoformat(),
        scope="Final Section 4.3.0 historical split/provider rules and Section 4.3.1 candidate construction; not a final fitted-model or event-study preregistration",
        supersedes_draft_snapshot="evidence/section4_3_0_split_protocol_DRAFT.json",
        development=source_specs,
        retrospective_evaluation=dict(source_epoch="RAW", calendar_start_inclusive="2025-01-01",
            first_session="2025-01-02", last_session="2026-10-12", sessions=445,
            calendar_minutes=173010, exposure="PRIOR_FEATURE_AND_MODEL_SELECTION_EXPOSURE",
            defensible_use="Descriptive temporal replication and prespecified sensitivity with explicit adaptive/exploratory label",
            disallowed_claim="Untouched, independent final test or selection-adjusted confirmatory significance",
            constructed_in_section4_3_1=False,
            per_target_last_eligible_session=dict(TLT="2026-10-12", HYG="2026-10-12", GOLD="2026-10-01", DOLLAR="2026-10-01")),
        exclusions=[dict(first_session="2002-12-30", last_session="2002-12-31", reason="Two-session legacy stub; excluded without inspecting outcomes"),
                    dict(first_calendar_date="2026-10-13", last_calendar_date="2026-10-28", reason="Outside frozen SPY panel; not certified unexposed and not silently promoted to a replacement holdout")],
        confirmatory_test=dict(status="NO_UNEXPOSED_PERIOD_IDENTIFIED", first_session=None, last_session=None,
            rule="A separate timestamped full-model/analysis lock and independent exposure audit must precede any new confirmatory period. Do not claim the current construction freeze locks an unbuilt detector.",
            new_data_collection_started=False),
        provider_eras=dict(LEGACY="PiTrading through 2022-03-04; inherited adjustment/cleaning; historical clock and possible centered cleaning remain unresolved",
            RAW="IEX-labelled audited RAW starts 2022-03-07; no further dividend scaling",
            boundary="No bridging return, rolling feature, volume history, scaler, HMM fit, or state recursion across provider eras; report eras separately",
            volume="Raw/log volume diagnostic candidates only; use same-provider same-slot relative volume for scale-comparable candidates; never pool raw volume across providers",
            causal_claim="Past-only implementation does not repair or certify upstream vendor noncausality"),
        clocks=dict(calendar="Inherited frozen XNYS RTH grid, New York DST and early closes",
            bar_label="Minute-start assumption inherited from Section 3; full bar available at stamp + 60 seconds",
            legacy_sensitivity="Later cross-asset timing must report legacy -1/0/+1 minute scenarios; primary clock remains conditional",
            overnight="No overnight returns; first-minute return absent every session",
            missing="No interpolation/fill; NaN is never zero; exact adjacent endpoints for 1m return",
            target_rule="No TLT/HYG/GOLD/DOLLAR return columns in Section 4.3.1; same-minute target reaction is descriptive"),
        nested_development=dict(train_sessions=252, inner_train_sessions=189, inner_validation_sessions=63,
            outer_development_sessions_max=126, outer_stride_sessions=126, terminal_outer_minimum=63,
            train_day_stride=1, validation_day_stride=1, source_file="development_nested_folds.csv",
            rule="Within each fold select using inner train/validation only; refit on preceding 252 sessions before outer development diagnostics. All features/scalers/models train chronologically; no selection on retrospective 2025-2026 or target reactions.",
            feature_history="Causal same-era volume history may carry from previous observed sessions; fold fit statistics use training rows only; no numeric history from the excluded 2002 stub",
            label="Development folds are not a newly restored clean final test"),
        windows_minutes=list(WINDOWS), candidate_features=registry,
        definitions=dict(return_1m="ln(C_t/C_(t-1)); exact consecutive within-session closes, decimals",
            strict="For W in 5,10,15,30,60: require W eligible returns ending at t, slot>=W. RV=sqrt(sum(r^2)); downside=sqrt(sum(min(r,0)^2)); strict momentum=sum(r)",
            endpoint_momentum="ln(C_t/C_(t-W)) for W in 5,10,15,30,60; exact two closes and same session. Interior gaps allowed; not an RV estimator",
            partial90="sqrt(W/n * sum(observed r^2)) with full W-minute clock window and n>=ceil(.90 W). All five W; downside variant at W=15. Proxy, no assertion of random gaps or unbiasedness",
            sampled5="rv60_sampled5_exact: sqrt(sum of twelve exact five-minute log returns squared), closes at t,t-5,...,t-60. Sliding phase; a different sampling-scale estimator",
            range="ln(High/Low) of current completed bar",
            volume="Raw and natural-log volume; log undefined for zero. relative_volume20=current volume/median positive same-slot volume from previous 20 scheduled sessions, at least 10 positives. Current zero ratio=0; log ratio unavailable",
            shock="(r_t-median(previous 60 exact returns))/(1.4826*MAD(previous 60)); require 61 consecutive eligible returns including current and positive MAD. No epsilon/fill for zero scale"),
        comparison_tiers=dict(core15=["return_1m","rv15_strict","downside15_strict","relative_volume20","intrabar_range_log"],
            strict60=["return_1m","rv15_strict","rv60_strict"],
            partial60=["return_1m","rv15_partial90","rv60_partial90"],
            sampled60=["return_1m","rv15_partial90","rv60_sampled5_exact"]),
        selection_guardrails=["No feature winner or model frequency selected by construction/coverage",
            "For later HMM candidate comparisons, common training support, train-only scalers, identical target timestamps, forward-filtered states, and paired F0 baseline within each tier",
            "Do not compare scores across tiers with different supports as if paired",
            "No full-era quantile thresholds, fitted normalizers or HMM in 4.3.1",
            "No nominal confirmatory p-values from exposed retrospective evaluation"],
        verification=["Independent formulas; missing-price and partial counts; session/halfday reset; prior-only volume; future edits/deletion; zero scales",
                      "Actual development masks, adjacent-close recomputation, no infinities, prefix deletion, source before/after SHA-256"],
        exposure_audit_file="exposure_audit.json", exposure_audit_sha256=sha256(ROOT/"exposure_audit.json"),
        evidence_inventory_sha256=sha256(ROOT/"evidence_inventory.csv"),
        development_folds_sha256=sha256(ROOT/"development_nested_folds.csv"),
        implementation_files=[dict(name=name, sha256=sha256(ROOT/name)) for name in
                              ["section4_3_1_candidates.py", "test_candidates.py", "audit_and_freeze.py"]],
        amendments="Never edit this frozen file. A new timestamp/hash plus a change log is required; prior exposure remains documented.")
    dump(frozen, protocol)
    digest = sha256(frozen)
    frozen.with_suffix(".sha256").write_text(f"{digest}  {frozen.name}\n", encoding="ascii")
    (ROOT/"FROZEN_PROTOCOL.txt").write_text(f"{frozen.name}\nSHA-256: {digest}\nFrozen UTC: {now.isoformat()}\nFrozen New York: {protocol['frozen_america_new_york']}\n", encoding="utf-8")
    print(json.dumps(dict(protocol_file=str(frozen), sha256=digest, exposure=exposure,
                         development=source_specs, development_folds=len(folds)), indent=2))


if __name__ == "__main__":
    main()
