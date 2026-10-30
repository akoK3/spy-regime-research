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
DATA = Path(r"C:\Users\kakij\OneDrive\Desktop\data\section4_3_rebuild_20261028")
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


def verify():
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


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "write": write_policy()
    elif mode == "verify": sys.exit(verify())
    else: sys.exit("usage: step5_policy.py write|verify")
