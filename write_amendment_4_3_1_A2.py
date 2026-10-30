#!/usr/bin/env python3
"""Write the dated, hashed Section 4.3.1 amendment A2 from the Step 4 measurement table.

The numbers are copied from step4_parameter_table.json (measured from the code), not typed.
Refuses to run if an A2 amendment already exists or if the source table is not the expected one.
"""
import json, hashlib, subprocess, datetime
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "section431_step3_all_in_one_results"
PROTO_DIR = Path(r"C:\Users\kakij\OneDrive\Desktop\data\section4_3_rebuild_20261028")
SOURCE_TABLE_SHA = "505f202d7d91a2b67cfa63f41f34cc2d1c146d10f7d15ac7a2971e3d72e33e97"
FROZEN = PROTO_DIR / "protocol_20261029T032641Z.json"
A1 = PROTO_DIR / "results" / "protocol_amendment_4_3_0_A1_20261029T034121Z.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


DEFINITIONS = {
    "close_location_proxy": ("close_location", "(Close-Low)/(High-Low) of the current completed bar; defined only if High>Low and the bar has Close>0, High>=Close>=Low, Low>0, Volume>=0, all finite"),
    "bipower": ("bipower", "(pi/2)*sum of |r_i||r_(i-1)| over the w-1 adjacent pairs of the w returns ending at t"),
    "jump_variation": ("jump_variation", "max(0, sum of r_i^2 over the w returns - bipower_w)"),
    "drawdown": ("drawdown", "Close_t / max(Close over t-w..t) - 1, from w+1 exact closes; zero or negative"),
    "amihud": ("amihud", "mean over the w bars of |r_i| / (Volume_i*Close_i); needs all volumes finite and dollar volume > 0"),
    "skew": ("skew", "mean(z^3) with z=(r-mean)/sd over the w returns, population sd (ddof=0); needs sd>0"),
    "kurtosis_excess": ("kurtosis_excess", "mean(z^4)-3 with the same z; needs sd>0"),
    "variance_ratio2": ("variance_ratio2", "mean((r_i+r_(i-1))^2) over adjacent pairs / (2*mean(r_i^2)); needs positive variance"),
    "directional_efficiency": ("directional_efficiency", "|ln(Close_t/Close_(t-w))| / sum|r_i| over the w returns; undefined if sum|r_i|=0"),
    "vol_of_vol": ("vol_of_vol", "sample SD (ddof=1) of the w/5 non-overlapping 5-return realized volatilities sqrt(sum r^2) in the window"),
    "extreme_loss": ("extreme_loss", "min(r_i) over the w returns"),
    "volume_variability": ("volume_variability", "SD(ddof=1)/mean of Volume over the w bars; needs mean>0; also requires the w returns to be finite"),
    "volume_adjusted_range": ("volume_adjusted_range", "mean over the w bars of ln(High/Low)/Volume; needs all Volume>0 and finite ranges; also requires the w returns to be finite"),
    "reversal": ("reversal", "1.0 if sign(sum of first w//2 returns) != sign(sum of the rest), else 0.0; undefined if either sum is 0"),
    "return_autocorr1": ("return_autocorr1", "Pearson correlation of (r_i, r_(i-1)) over the w-1 adjacent pairs; needs both SDs > 0"),
}
LM_STAT = "r_t / sqrt((pi/2) * (1/59) * sum of |r_i||r_(i-1)| over the 59 adjacent pairs of the 60 prior returns); the current return is excluded from the scale; needs 60 finite prior returns, finite r_t and scale>0"
LM_JUMP = "1.0 if |lee_mykland_approx60| > c0 - s0*ln(-ln(1-alpha)) with n=390, alpha=0.01 (threshold 5.4667), else 0.0; undefined where the statistic is undefined; c0=sqrt(2 ln n)/sqrt(2/pi)-(ln pi+ln ln n)/(2*sqrt(2/pi)*sqrt(2 ln n)), s0=1/(sqrt(2/pi)*sqrt(2 ln n))"


def describe(name):
    if name == "close_location_proxy":
        return "close_location", DEFINITIONS[name][1], "step3_all_in_one.py construct_deferred (ported from section-4.3.1.py close_location)"
    if name == "lee_mykland_approx60":
        return "lee_mykland", LM_STAT, "step3_all_in_one.py construct_deferred (ported from section-4.3.1.py lm_stat60)"
    if name == "lee_mykland_jump60":
        return "lee_mykland", LM_JUMP, "step3_all_in_one.py construct_deferred (ported from section-4.3.1.py lm_jump60)"
    family, w = name.rsplit("_", 1)
    return DEFINITIONS[family][0], f"{DEFINITIONS[family][1]} (w={w})", "section431_additions.py construct_additions"


def main():
    assert not list(OUT.glob("amendment_4_3_1_A2_*.json")), "an A2 amendment already exists; never overwrite"
    assert sha(OUT / "step4_parameter_table.json") == SOURCE_TABLE_SHA, "Step 4 source table is not the one this amendment is based on"
    table = json.loads((OUT / "step4_parameter_table.json").read_text(encoding="utf-8"))
    rows = {r["output"]: r for r in table["rows"]}
    new = [r for r in table["rows"] if r["status"] == "NO_SPEC"]
    frozen_names = [r["output"] for r in table["rows"] if r["status"] == "PASS"]
    assert len(new) == 45 and len(frozen_names) == 35 and rows["overnight_return_open"]["status"] == "FAIL"

    specs = []
    for r in new:
        e = r["extracted"]
        family, definition, source = describe(r["output"])
        specs.append(dict(output=r["output"], family=family, definition=definition, source=source,
                          lookback_bars=e["L"], lookback_sessions=e["S"],
                          min_valid_obs=dict(count=e["min"], unit={"ret": "returns", "bar": "bars", "sess": "sessions"}[e["kind"]]),
                          warmup=dict(first_slot=e["slot"], first_session=e["sess"])))

    now = datetime.datetime.now(datetime.timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    ny = pd.Timestamp(now).tz_convert("America/New_York").isoformat()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    ov = rows["overnight_return_open"]["extracted"]
    files = {
        "step3_all_in_one.py": ROOT / "step3_all_in_one.py",
        "step4_extract_parameters.py": ROOT / "step4_extract_parameters.py",
        "section431_additions.py": ROOT / "section431_step3_verification" / "prototype_sources" / "section431_additions.py",
        "section4_3_1_candidates.py": ROOT / "section431_step3_verification" / "prototype_sources" / "section4_3_1_candidates.py",
        "step3_RAW_report.json": OUT / "step3_RAW_report.json",
        "step3_LEGACY_report.json": OUT / "step3_LEGACY_report.json",
        "step4_parameter_table.json": OUT / "step4_parameter_table.json",
    }
    amendment = {
        "amendment": "4.3.1-A2",
        "created_utc": now.isoformat(),
        "created_america_new_york": ny,
        "status": "SPECIFICATION_WRITTEN_AFTER_IMPLEMENTATION",
        "written_after_implementation": {
            "statement": "These specifications were written AFTER the 45 outputs were implemented, run and measured. They describe what the code does; they were not set before the code existed and must not be presented as preregistered or ex ante. Passing the Step 4 comparison shows the code still behaves as written here, not that these choices were made in advance.",
            "implementation_and_evidence_sha256": {k: sha(v) for k, v in files.items()},
            "evidence_git_commit": head,
            "values_source": "Measured from the code by step4_extract_parameters.py; copied into this file by write_amendment_4_3_1_A2.py, not typed.",
        },
        "basis": {
            "frozen_protocol": {"file": FROZEN.name, "sha256": sha(FROZEN), "change": "none; its 35 candidate features and definitions are unchanged"},
            "amendment_proposal_A1": {"file": A1.name, "sha256": sha(A1), "relation": "A1 stays an unapproved proposal; this amendment does not approve it. It replaces A1's max_feature_lookback_minutes=60 with the cap defined below for the detector features."},
        },
        "cap": {
            "max_prior_bars": 60,
            "definition": "A detector feature at bar t may use the returns of the 60 bars before t (t-60..t-1) and of bar t itself. The close of the bar before the earliest used return is only the reference price of that return and is not counted as a further bar. Same session only; no interpolation or fill.",
            "step4_lookback_limit_bars": 61,
            "step4_lookback_meaning": "Step 4 'lookback' is the distance from t to the earliest close an output uses. Return-based outputs with 60 prior returns plus the current one reach c[t-61], so the limit is 61 in those units.",
            "frozen_outputs_inside_cap": "shock_prior60_mad (frozen) uses 60 prior returns plus the current return (Step 4 lookback 61) and is inside the cap by this definition. A literal cap that counted the reference close as a 61st prior bar would exclude it and the Lee-Mykland outputs.",
            "not_changed": "relative_volume20 keeps its frozen cross-session history of 20 same-slot sessions; this cap is a within-session limit.",
        },
        "excluded_from_detector_features": [{
            "output": "overnight_return_open",
            "reserved_for": "the overnight analysis, to be specified separately",
            "reason": "The frozen protocol says 'No overnight returns; first-minute return absent every session'. The output also reaches back to the session open and the prior session (Step 4 lookback %d bars and %d session), beyond the cap." % (ov["L"], ov["S"]),
            "rule": "Must not be an input to the detector, any scaler or any HMM. The audit script may keep computing it for its own checks.",
            "measured": {"lookback_bars": ov["L"], "lookback_sessions": ov["S"], "min_valid_bars": ov["min"], "first_session": ov["sess"]},
        }],
        "detector_feature_outputs": {"count": 80, "frozen_protocol_outputs": frozen_names, "specified_by_this_amendment": [s["output"] for s in specs]},
        "missing_data_rule": "Inherited from the frozen protocol: no interpolation or fill; NaN is never zero; an output is NaN unless its minimum valid observations are present.",
        "specified_outputs": specs,
        "unchanged": ["all 35 frozen candidate features and definitions", "provider-era separation", "no fitted model, scaler or threshold selection in 4.3.1"],
        "verification": "step4_extract_parameters.py re-measures lookback, minimum valid observations and warmup from the code and compares them with the frozen protocol and this amendment.",
    }
    path = OUT / f"amendment_4_3_1_A2_{stamp}.json"
    data = (json.dumps(amendment, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    path.with_suffix(".sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    print(path.name)
    print("SHA-256:", digest)
    print("created_utc:", now.isoformat(), "| NY:", ny)
    print("specified outputs:", len(specs), "| detector outputs: 80 | excluded: overnight_return_open")


if __name__ == "__main__":
    main()
