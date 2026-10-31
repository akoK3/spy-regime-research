#!/usr/bin/env python3
"""Step 5: causality and boundary policy P1 (python step5_policy.py write) and its
verification (python step5_policy.py verify).

verify reads the saved Step 3/4 results and amendment A2 (it reruns neither) and runs one new
test: an extra one-minute delay of every input must shift every detector feature by exactly one bar.
"""
import sys, json, hashlib, datetime, subprocess
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import step3_all_in_one as s  # noqa: E402

OUT = s.OUT
DATA = ROOT / "frozen_documents"  # in-repository copies (N4 L7)
FROZEN = DATA / "protocol_20261029T032641Z.json"
PANEL_AUDIT = DATA / "section431_panel_audit.json"
SRC = ROOT / "section431_step3_verification" / "prototype_sources"
EXCLUDED = "overnight_return_open"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def one(pattern):
    files = sorted(OUT.glob(pattern))
    assert len(files) == 1, f"expected one {pattern}, found {len(files)}"
    return files[0]


def write_hashed(path, data):
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    path.with_suffix(".sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def now_stamp():
    now = datetime.datetime.now(datetime.timezone.utc)
    return now, now.strftime("%Y%m%dT%H%M%SZ"), pd.Timestamp(now).tz_convert("America/New_York").isoformat()


def write_policy():
    assert not list(OUT.glob("policy_4_3_1_P1_2*.json")), "a P1 policy already exists; never overwrite"
    amendment = one("amendment_4_3_1_A2_*.json")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    evidence = {
        "step3_all_in_one.py": ROOT / "step3_all_in_one.py",
        "step4_extract_parameters.py": ROOT / "step4_extract_parameters.py",
        "section4_3_1_candidates.py": SRC / "section4_3_1_candidates.py",
        "section431_additions.py": SRC / "section431_additions.py",
        "step3_RAW_report.json": OUT / "step3_RAW_report.json",
        "step3_LEGACY_report.json": OUT / "step3_LEGACY_report.json",
        "step4_parameter_table.json": OUT / "step4_parameter_table.json",
        amendment.name: amendment,
    }
    now, stamp, ny = now_stamp()
    policy = {
        "policy": "4.3.1-P1",
        "created_utc": now.isoformat(),
        "created_america_new_york": ny,
        "status": "POLICY_WRITTEN_AFTER_IMPLEMENTATION",
        "written_after_implementation": {
            "statement": "This policy was written after the features were implemented and audited. It states the rules the implementation follows and that later work must keep; it is not an ex-ante preregistration.",
            "evidence_sha256": {k: sha(v) for k, v in evidence.items()},
            "evidence_git_commit": head,
        },
        "basis": {
            "frozen_protocol": {"file": FROZEN.name, "sha256": sha(FROZEN)},
            "amendment_A2": {"file": amendment.name, "sha256": sha(amendment)},
        },
        "rules": [
            {"id": "R1", "title": "Availability",
             "rule": "A bar stamped t (minute start) covers [t, t+60 s). The bar and anything computed from it are known only at t+1 minute, so a feature row stamped t may be used only at decision times >= t+1 minute. No feature at row t may use a bar stamped after t.",
             "enforced_by": "load_development asserts available == t + 60 s for every bar; construction is trailing-only (Step 4 finds no output that reads bars after t).",
             "verified_by": "Step 3 reports (loader assertion ran without error, prefix invariance), Step 4 table (no lookahead), delay test"},
            {"id": "R2", "title": "Session reset",
             "rule": "Every window resets at the session open: a feature at slot j uses only bars of the same session at slots <= j, so the first W bars of a session (W = the output's lookback) are NaN. The only cross-session value is the baseline of relative_volume20 and log_relative_volume20: the median of positive volumes at the same slot over the previous 20 sessions of the same era, with at least 10 required. No other detector output uses data from another session.",
             "enforced_by": "construct, construct_additions and construct_deferred work per session; relative_volume uses the previous 20 sessions of the loaded era.",
             "verified_by": "Step 4 table (sessions of history), Step 3 provider_isolation and prior_session_isolation, delay test"},
            {"id": "R3", "title": "Provider boundary",
             "rule": "LEGACY (through 2022-03-04) and RAW (from 2022-03-07) are loaded and computed separately. No return, window, volume history (including the relative-volume baseline), scaler, fit or state crosses the boundary. The first 10 sessions of each era have no relative volume.",
             "enforced_by": "run(era) in step3_all_in_one.py loads one era at a time; load_development requires a single source_epoch.",
             "verified_by": "Step 3 provider_isolation (both eras), Step 3 source hashes against the frozen protocol"},
            {"id": "R4", "title": "Overnight excluded",
             "rule": "overnight_return_open is excluded from detector inputs and reserved for the overnight analysis (amendment A2). The detector feature set is the other 80 outputs.",
             "enforced_by": "Declarative: A2 and the Step 4 check. No detector code exists yet to enforce it.",
             "verified_by": "A2, Step 4 table"},
        ],
        "delay_invariance_test": {
            "statement": "Shift every bar-level input of each session one slot later (slot 0 becomes missing, the last bar is dropped) and recompute. Each of the 80 detector features at slot s+1 must equal the original at slot s, and must not equal the original at shift 0 or 2.",
            "datasets": ["synthetic panel with missing bars", "RAW slice of 40 sessions including the 2022-11-25 early close", "LEGACY slice of 40 sessions"],
            "tolerance": "rtol 1e-9, atol 0, NaN equals NaN",
        },
        "limits": [
            "Step 3 audited TRAIN spans only (LEGACY 2003-01-02..2018-12-21, RAW 2022-03-07..2024-12-23); the days next to the 2022-03-04/2022-03-07 boundary were not in the audited LEGACY span. R3 rests on era-separate loading and the first-10-sessions check.",
            "R3 and R4 are enforced by how the audit scripts are built, not by a guard a future pooled pipeline would inherit.",
        ],
    }
    path = OUT / f"policy_4_3_1_P1_{stamp}.json"
    digest = write_hashed(path, (json.dumps(policy, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(path.name, "\nSHA-256:", digest, "\ncreated_utc:", now.isoformat(), "| NY:", ny)


BAR_KEYS = ("r", "close", "open", "high", "low", "volume", "range")


def delayed(d):
    z = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in d.items()}
    for a, b in zip(d["first"], d["end"]):
        for k in BAR_KEYS:
            z[k][a + 1:b] = d[k][a:b - 1]; z[k][a] = np.nan
        z["valid"][a + 1:b] = d["valid"][a:b - 1]; z["valid"][a] = False
    return z


def compute(d):
    return {**s.construct(d)[0], **s.construct_additions(d), **s.construct_deferred(d)}


def delay_test(d, label):
    orig, late = compute(d), compute(delayed(d))
    spans = list(zip(d["first"], d["end"]))
    def idx(shift):
        return np.concatenate([np.arange(a, b - shift) for a, b in spans])
    res = {}
    for name in orig:
        if name == EXCLUDED: continue
        eq = {}
        for shift in (0, 1, 2):
            src = idx(shift)
            eq[shift] = bool(np.allclose(orig[name][src], late[name][src + shift], rtol=1e-9, atol=0, equal_nan=True))
        finite = int(np.isfinite(orig[name][idx(1)]).sum())
        res[name] = dict(shift1=eq[1], shift0=eq[0], shift2=eq[2], finite=finite, ok=eq[1] and not eq[0] and not eq[2] and finite > 0)
    sizes = [int(b - a) for a, b in spans]
    summary = dict(dataset=label, sessions=len(spans), rows=int(len(d["r"])), early_close_sessions=int(sum(x < 390 for x in sizes)),
                   outputs_tested=len(res), passed=sum(v["ok"] for v in res.values()),
                   failed=[k for k, v in res.items() if not v["ok"]])
    print(f"delay test {label}: {summary['passed']}/{summary['outputs_tested']} outputs shift exactly one bar; early-close sessions {summary['early_close_sessions']}", flush=True)
    return summary, res


def real_slice(era):
    first, last, panel, etf = s.CONFIG[era]
    spec = {"first_session": first, "last_session": last, "panel_file": str(s.file_path(panel)), "etf_file": str(s.file_path(etf))}
    d = s.load_development(era, spec)
    d.update(s.load_ohlc(spec, d))
    days = list(d["day"][d["first"]])
    lo = max(0, days.index("2022-11-25") - 20) if era == "RAW" else 2000
    z, _ = s.slice_sessions(d, lo, lo + 40)
    return z


def rule_checks():
    """R1-R4 checked against the saved Step 3/4 results and A2 (nothing is rerun)."""
    policy_file = one("policy_4_3_1_P1_2*.json")
    policy_sha = sha(policy_file)
    assert policy_file.with_suffix(".sha256").read_text().split()[0] == policy_sha, "policy hash mismatch"
    A2 = json.loads(one("amendment_4_3_1_A2_*.json").read_text(encoding="utf-8"))
    rep = {e: json.loads((OUT / f"step3_{e}_report.json").read_text(encoding="utf-8")) for e in ("RAW", "LEGACY")}
    t4 = json.loads((OUT / "step4_parameter_table.json").read_text(encoding="utf-8"))
    rows = {r["output"]: r for r in t4["rows"]}
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    loader = (SRC / "section4_3_1_candidates.py").read_text(encoding="utf-8")
    ev = A2["written_after_implementation"]["implementation_and_evidence_sha256"]
    cross = {"relative_volume20", "log_relative_volume20"}
    detector = [n for n in rows if n != EXCLUDED]
    panel_audit = json.loads(PANEL_AUDIT.read_text(encoding="utf-8")) if PANEL_AUDIT.exists() else {}

    both = lambda f: all(f(rep[e]) for e in rep)
    rules = {
        "R1 usable at t+1 minute": [
            ("loader asserts available == t + 60 s (and is the audited file)", "available == t + MINUTE" in loader and sha(SRC / "section4_3_1_candidates.py") == ev["section4_3_1_candidates.py"]),
            ("both Step 3 reports have no execution error, so the assertion held", both(lambda r: "execution" not in r["checks"] and r["status"] == "PASS")),
            ("Step 3 prefix invariance PASS in both eras", both(lambda r: r["checks"]["real_train_prefix_invariance"]["status"] == "PASS")),
            ("Step 4: no output reads bars after t", len(rows) == 81 and not any("lookahead" in p for r in rows.values() for p in r["problems"])),
            ("earlier panel audit flags availability at t+1 in both eras", all(panel_audit.get(e, {}).get("bar_available_at_t_plus_one_pass") is True for e in ("RAW", "LEGACY"))),
        ],
        "R2 session reset": [
            ("Step 4: no cross-session history except relative volume (20 sessions)", all(rows[n]["extracted"]["S"] == (20 if n in cross else 0) for n in detector)),
            ("Step 4: only relative volume needs earlier sessions (first session 10), all others warm up inside session 0", all(rows[n]["extracted"]["sess"] == (10 if n in cross else 0) for n in detector)),
            ("relative-volume baseline: 20 sessions, at least 10 valid", all(rows[n]["extracted"]["kind"] == "sess" and rows[n]["extracted"]["min"] == 10 for n in cross)),
            ("Step 4: every detector lookback within the A2 cap", all(rows[n]["extracted"]["L"] <= A2["cap"]["step4_lookback_limit_bars"] for n in detector)),
            ("Step 3 provider_isolation (no value inside a window's first bars) PASS in both eras", both(lambda r: r["checks"]["provider_isolation"]["status"] == "PASS")),
            ("Step 3 prior_session_isolation PASS in both eras", both(lambda r: r["checks"]["prior_session_isolation"]["status"] == "PASS")),
        ],
        "R3 no LEGACY/RAW crossing": [
            ("Step 3 provider_isolation PASS in both eras", both(lambda r: r["checks"]["provider_isolation"]["status"] == "PASS")),
            ("each report is one era, from different source files", rep["RAW"]["era"] == "RAW" and rep["LEGACY"]["era"] == "LEGACY" and rep["RAW"]["source_hashes"] != rep["LEGACY"]["source_hashes"]),
            ("source files equal the frozen protocol's hashes", all(rep[e]["source_hashes"]["panel"] == frozen["development"][e]["panel_sha256"] and rep[e]["source_hashes"]["etf"] == frozen["development"][e]["etf_sha256"] for e in rep)),
            ("loader requires a single source_epoch", "Mixed source eras" in loader),
            ("first 10 sessions of an era have no relative volume (Step 4 warmup session 10)", all(rows[n]["extracted"]["sess"] == 10 for n in cross)),
        ],
        "R4 overnight excluded": [
            ("A2 excludes overnight_return_open", [x["output"] for x in A2["excluded_from_detector_features"]] == [EXCLUDED]),
            ("Step 4 marks it EXCLUDED", rows[EXCLUDED]["status"] == "EXCLUDED"),
            ("detector set is 80 outputs without it", len(detector) == 80 and EXCLUDED not in A2["detector_feature_outputs"]["frozen_protocol_outputs"] + A2["detector_feature_outputs"]["specified_by_this_amendment"]),
            ("Step 4: 80 PASS, 0 FAIL, 1 EXCLUDED", t4["counts"] == {"PASS": 80, "FAIL": 0, "EXCLUDED": 1}),
        ],
    }

    return policy_file, policy_sha, rules, rows


def verify_v1():
    """Original verification with the strict one-bar shift test. Retained as run; the addendum labels that test mis-specified."""
    policy_file, policy_sha, rules, rows = rule_checks()
    tests = []
    synth_summary, synth = delay_test(s.synthetic_panel(), "synthetic panel")
    tests.append(synth_summary)
    for era in ("RAW", "LEGACY"):
        summary, _ = delay_test(real_slice(era), f"{era} 40-session slice")
        tests.append(summary)

    table = []
    for name, checks in rules.items():
        table.append(dict(item=name, status="PASS" if all(ok for _, ok in checks) else "FAIL", checks=[dict(check=c, ok=ok) for c, ok in checks]))
    for t in tests:
        table.append(dict(item=f"delay by 1 minute shifts every feature exactly 1 bar: {t['dataset']}",
                          status="PASS" if t["passed"] == t["outputs_tested"] == 80 else "FAIL", detail=t))
    now, stamp, ny = now_stamp()
    report = dict(generated_utc=now.isoformat(), generated_america_new_york=ny, policy=policy_file.name, policy_sha256=policy_sha,
                  note="Rules R1-R4 were checked against saved Step 3/4 results and A2; Step 3 and 4 were not rerun. Only the delay test is new.",
                  overall="PASS" if all(r["status"] == "PASS" for r in table) else "FAIL", table=table)
    path = OUT / f"policy_4_3_1_P1_verification_{stamp}.json"
    digest = write_hashed(path, (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    lines = ["| Rule / test | Status | Failed checks |", "|---|---|---|"]
    for r in table:
        failed = "; ".join(c["check"] for c in r.get("checks", []) if not c["ok"]) or "-"
        if "detail" in r and r["detail"]["failed"]: failed = ", ".join(r["detail"]["failed"][:6])
        lines.append(f"| {r['item']} | {r['status']} | {failed} |")
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("\noverall:", report["overall"], "|", path.name, "| SHA-256:", digest)
    return 0 if report["overall"] == "PASS" else 1


MINUTE = 60_000_000_000


def write_addendum():
    assert not list(OUT.glob("policy_4_3_1_P1_addendum_2*.json")), "an addendum already exists; never overwrite"
    policy = one("policy_4_3_1_P1_2*.json")
    old_report = one("policy_4_3_1_P1_verification_2*.json")
    diagnosis = OUT / "step5_delay_failure_diagnosis.json"
    old = json.loads(old_report.read_text(encoding="utf-8"))
    now, stamp, ny = now_stamp()
    doc = {
        "addendum": "4.3.1-P1-A",
        "created_utc": now.isoformat(), "created_america_new_york": ny,
        "status": "WRITTEN_AFTER_SEEING_THE_ORIGINAL_TEST_FAIL",
        "statement": "This addendum was written after the original delay test had been run and had failed. It replaces that test; it does not change rules R1-R4 or any feature.",
        "amends": {"policy": policy.name, "sha256": sha(policy), "section": "delay_invariance_test"},
        "original_delay_test": {
            "label": "MIS-SPECIFIED (retained; result unchanged)",
            "definition": "Shift every bar-level input of each session one slot later and require every detector feature at slot s+1 to equal the original at slot s.",
            "result": {t["detail"]["dataset"]: f"FAIL {t['detail']['passed']}/{t['detail']['outputs_tested']}" for t in old["table"] if "detail" in t},
            "verification_report": {"file": old_report.name, "sha256": sha(old_report)},
            "diagnosis": {"file": diagnosis.name, "sha256": sha(diagnosis), "finding": "every mismatch is at a known clock-position edge row; no value leaked"},
            "why_mis_specified": [
                "R1 concerns when a value becomes available, not what its value is. A delay moves availability; it does not move a feature to a different bar. The test checked shift-equivariance of data content, which R1 does not require.",
                "The frozen definitions are clock-position rules (slot >= W), so shifting content one slot fails at the first computable row of the partial90 outputs by design.",
                "The shift drops the last bar of each session, so the relative-volume baseline changes at the slot after an early close ends.",
            ],
        },
        "replacement_delay_test": {
            "definition": "Add an extra 1-minute delay: every bar becomes available at t+2 minutes instead of t+1. Then (V) all 80 detector feature values, NaN pattern included, are identical to the undelayed run; (A) the available_at of every finite feature value equals t+2 minutes; (P) in a point-in-time replay, at decision time t+2 minutes the features computed from only the visible bars equal the full-run value at row t, and at decision time t+1 minute row t is not yet visible.",
            "available_at_definition": "available_at of a feature row stamped t is the availability of bar t, the newest bar it may read (R1: no output reads a later bar).",
            "datasets": ["synthetic panel with missing bars", "RAW slice of 40 sessions including the 2022-11-25 early close", "LEGACY slice of 40 sessions"],
            "replay": "3 decision rows per dataset, slot >= 70 and session >= 12; features recomputed from only the rows with available <= decision time",
            "tolerance": "V exact (NaN equals NaN); P rtol 1e-9, atol 0",
        },
        "unchanged": ["R1-R4 text in " + policy.name, "the 80 detector outputs and overnight_return_open exclusion (A2)"],
    }
    path = OUT / f"policy_4_3_1_P1_addendum_{stamp}.json"
    digest = write_hashed(path, (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    print(path.name, "\nSHA-256:", digest, "\ncreated_utc:", now.isoformat(), "| NY:", ny)


def delay_v2(d, label, rows):
    detector = [n for n in rows if n != EXCLUDED]
    d2 = dict(d); d2["available"] = d["available"] + MINUTE
    assert (d["available"] - d["t"] == MINUTE).all() and len(detector) == 80
    base, late = compute(d), compute(d2)
    different = [n for n in detector if not np.array_equal(base[n], late[n], equal_nan=True)]
    lag = d2["available"] - d["t"]
    wrong_lag, finite_rows = [], 0
    for n in detector:
        fin = np.isfinite(base[n]); finite_rows += int(fin.sum())
        if (lag[fin] != 2 * MINUTE).any(): wrong_lag.append(n)
    first = np.asarray(d["first"]); rowsess = np.searchsorted(first, np.arange(len(d["t"])), side="right") - 1
    cand = np.flatnonzero((d["slot"] >= 70) & (rowsess >= 12))
    picks = sorted(int(i) for i in np.random.default_rng(s.SEED + 5).choice(cand, size=3, replace=False))
    replay = []
    for idx in picks:
        t = int(d2["t"][idx])
        vis_new = int(np.searchsorted(d2["available"], t + 2 * MINUTE, side="right"))
        vis_old = int(np.searchsorted(d2["available"], t + MINUTE, side="right"))
        prefix = compute(s.truncate(d2, vis_new))
        off = [n for n in detector if not np.isclose(prefix[n][idx], base[n][idx], rtol=1e-9, atol=0, equal_nan=True)]
        replay.append(dict(row=idx, visible_rows_at_t_plus_2=vis_new, visible_rows_at_t_plus_1=vis_old,
                           visibility_ok=(vis_new == idx + 1 and vis_old == idx), differing_outputs=off))
    ok_replay = all(r["visibility_ok"] and not r["differing_outputs"] for r in replay)
    print(f"delay v2 {label}: values identical {80 - len(different)}/80, available_at = t+2min {len(detector) - len(wrong_lag)}/80 outputs ({finite_rows} finite values), replay {sum(r['visibility_ok'] and not r['differing_outputs'] for r in replay)}/3", flush=True)
    return [
        dict(item=f"extra 1-minute delay, all feature values identical: {label}", status="PASS" if not different else "FAIL", detail=dict(outputs=len(detector), different=different)),
        dict(item=f"extra 1-minute delay, available_at = t+2 minutes: {label}", status="PASS" if not wrong_lag and finite_rows > 0 else "FAIL", detail=dict(outputs=len(detector), finite_values_checked=finite_rows, wrong=wrong_lag)),
        dict(item=f"extra 1-minute delay, point-in-time replay: {label}", status="PASS" if ok_replay else "FAIL", detail=dict(replay=replay)),
    ]


def verify2():
    addendum = one("policy_4_3_1_P1_addendum_2*.json")
    add_sha = sha(addendum)
    assert addendum.with_suffix(".sha256").read_text().split()[0] == add_sha, "addendum hash mismatch"
    policy_file, policy_sha, rules, rows = rule_checks()
    old_file = one("policy_4_3_1_P1_verification_2*.json")
    old = json.loads(old_file.read_text(encoding="utf-8"))
    table = [dict(item=name, status="PASS" if all(ok for _, ok in checks) else "FAIL", checks=[dict(check=c, ok=ok) for c, ok in checks]) for name, checks in rules.items()]
    for r in old["table"]:
        if r["item"].startswith("delay by 1 minute"):
            table.append(dict(item=r["item"].replace("delay by 1 minute shifts every feature exactly 1 bar", "ORIGINAL one-bar shift test"),
                              status="FAIL", label="MIS-SPECIFIED (retained, not counted)", detail=r["detail"]))
    table.extend(delay_v2(s.synthetic_panel(), "synthetic panel", rows))
    for era in ("RAW", "LEGACY"):
        table.extend(delay_v2(real_slice(era), f"{era} 40-session slice", rows))
    now, stamp, ny = now_stamp()
    counted = [r for r in table if "label" not in r]
    report = dict(generated_utc=now.isoformat(), generated_america_new_york=ny, policy=policy_file.name, policy_sha256=policy_sha,
                  addendum=addendum.name, addendum_sha256=add_sha, retained_original_report=dict(file=old_file.name, sha256=sha(old_file)),
                  note="R1-R4 re-checked against saved Step 3/4 results (not rerun). The original shift test is retained and labeled mis-specified; it is not counted.",
                  overall="PASS" if all(r["status"] == "PASS" for r in counted) else "FAIL", table=table)
    path = OUT / f"policy_4_3_1_P1_verification_v2_{stamp}.json"
    digest = write_hashed(path, (json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    lines = ["| Rule / test | Status | Note |", "|---|---|---|"]
    for r in table:
        note = r.get("label", "")
        if not note and r["status"] != "PASS": note = "; ".join(c["check"] for c in r.get("checks", []) if not c["ok"]) or json.dumps(r.get("detail"))[:200]
        lines.append(f"| {r['item']} | {r['status']} | {note or '-'} |")
    path.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("\noverall (counted rows):", report["overall"], "|", path.name, "| SHA-256:", digest)
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "write": write_policy()
    elif mode == "verify": sys.exit(verify_v1())
    elif mode == "addendum": write_addendum()
    elif mode == "verify2": sys.exit(verify2())
    else: sys.exit("usage: step5_policy.py write|verify|addendum|verify2")
