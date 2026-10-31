#!/usr/bin/env python3
"""Write the Section 4.3.1 closing report (SECTION_4_3_1_CLOSED) from saved results only.
Reads the committed reports, amendments, policies and coverage; reruns nothing. Refuses to overwrite."""
import json, hashlib, subprocess, datetime, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
R = ROOT / "section431_step3_all_in_one_results"
FZ = ROOT / "frozen_documents"
EXCLUDED = "overnight_return_open"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def one(pattern, base=R):
    files = sorted(base.glob(pattern))
    assert len(files) == 1, f"expected one {pattern}, found {len(files)}"
    return files[0]


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main():
    assert not list(R.glob("section_4_3_1_closing_report_2*.json")), "closing report exists; never overwrite"
    proto_f = FZ / "protocol_20261029T032641Z.json"
    assert sha(proto_f) == "3d6f0c96fce1c05f8e94d1a8c6e6b14a5b5b1c9f013e6a95dd1e96498cbfff8b"
    proto = load(proto_f)
    cov_f = FZ / "protocol_amendment_431_A2_FROZEN_coverage.json"
    a1_f = FZ / "protocol_amendment_4_3_0_A1_20261029T034121Z.json"
    a2_f = one("amendment_4_3_1_A2_*.json")
    pol_f, add_f = one("policy_4_3_1_P1_2*.json"), one("policy_4_3_1_P1_addendum_2*.json")
    v1_f, v2_f = one("policy_4_3_1_P1_verification_2*.json"), one("policy_4_3_1_P1_verification_v2_*.json")
    a2, v2, cov = load(a2_f), load(v2_f), load(R / "step6_coverage_TRAIN.json")
    t4 = load(R / "step4_parameter_table.json")
    rep = {e: load(R / f"step3_{e}_report.json") for e in ("RAW", "LEGACY")}
    m2 = pd.read_csv(ROOT / "section431_step2_final_audit" / "feature_family_eligibility_matrix.csv")
    s2 = {e: load(ROOT / "section431_step2_final_audit" / f"{e}_summary.json") for e in ("LEGACY", "RAW")}
    assert t4["counts"] == {"PASS": 80, "FAIL": 0, "EXCLUDED": 1} and v2["overall"] == "PASS"
    assert all(r["status"] == "PASS" for r in rep.values()) and cov["counts"] == {"PASS": 20, "BELOW": 60}

    # ---- feature dictionary
    d = proto["definitions"]
    def frozen_def(n):
        if n == "return_1m": return d["return_1m"]
        if n == "abs_return_1m": return "absolute value of return_1m"
        if n == "intrabar_range_log": return d["range"]
        if n in ("raw_volume", "log_raw_volume", "relative_volume20", "log_relative_volume20"): return d["volume"]
        if n == "rv60_sampled5_exact": return d["sampled5"]
        if n == "shock_prior60_mad": return d["shock"]
        if n.endswith("_endpoint"): return d["endpoint_momentum"]
        if n.endswith("_partial90"): return d["partial90"]
        if n.endswith("_strict"): return d["strict"]
        raise KeyError(n)
    a2defs = {x["output"]: x for x in a2["specified_outputs"]}
    covcols = {c["column"]: c for c in cov["columns"]}
    dictionary = []
    for r in t4["rows"]:
        n, e = r["output"], r["extracted"]
        if n == EXCLUDED:
            definition = "log(Open of the session's first bar / Close of the previous session's last bar), assigned to every bar of the session; NaN for the era's first session or if either price is missing/non-positive"
            spec_by, role, c = "A2 exclusion", "EXCLUDED from detector inputs (reserved for the overnight analysis)", None
        elif n in a2defs:
            definition, spec_by, role, c = a2defs[n]["definition"], "A2 (4.3.1-A2)", "detector", covcols[n]
        else:
            definition, spec_by, role, c = frozen_def(n), "frozen protocol", "detector", covcols[n]
        unit = {"ret": "returns", "bar": "bars", "sess": "sessions"}[e["kind"]]
        dictionary.append(dict(output=n, role=role, specified_by=spec_by, definition=definition, lookback_bars=e["L"], lookback_sessions=e["S"],
                               min_valid_obs=f"{e['min']} {unit}", warmup=f"slot {e['slot']} / session {e['sess']}", step4_status=r["status"],
                               coverage_LEGACY_pct=None if c is None else c["LEGACY_pct"], coverage_RAW_pct=None if c is None else c["RAW_pct"],
                               coverage_status=None if c is None else c["status"]))

    # ---- documents and hashes
    documents = [
        ("Frozen protocol v2 (35 candidate features, split, clocks)", proto_f, "frozen 2026-10-29T03:26:41Z", "original: Desktop\\data\\section4_3_rebuild_20261028"),
        ("Frozen protocol v1 (superseded)", FZ / "protocol_20261029T032504Z.json", "2026-10-29T03:25:04Z", "original: same folder"),
        ("Amendment 4.3.0-A1 (proposal, NOT approved)", a1_f, "2026-10-29T03:41:21Z", "original: ...\\section4_3_rebuild_20261028\\results"),
        ("Coverage amendment 4.3.1-A2-post-screening (80% floor, denominator)", cov_f, "2026-10-30", "original: Downloads\\section431_step2_final_audit\\protocol_amendment_431_A2_FROZEN.json"),
        ("Amendment 4.3.1-A2 (45 added outputs, cap, overnight exclusion)", a2_f, a2["created_utc"], "this repo"),
        ("Policy 4.3.1-P1 (causality and boundary)", pol_f, load(pol_f)["created_utc"], "this repo"),
        ("Policy addendum 4.3.1-P1-A (delay test replaced)", add_f, load(add_f)["created_utc"], "this repo"),
    ]
    tracked = [p for p in git("ls-files").splitlines() if p != ".gitignore" or True]
    inventory = [dict(path=p, sha256=sha(ROOT / p)) for p in tracked]

    # ---- steps
    meets = m2[m2.coverage_screen == "MEETS_FROZEN_FLOOR"].feature_family.tolist()
    below = m2[m2.coverage_screen == "BELOW_FROZEN_FLOOR"].feature_family.tolist()
    steps = [
        ("1", "Baseline inputs (the label 'Step 1' is not defined in any file; this lists what Steps 2-6 rely on)",
         "Frozen protocol v2 with 35 candidate features built on the development rows (REPORT.md: 2,150,970 minute rows); test_candidates.py 6/6 pass; panel audit PASS in both eras (TRAIN rows LEGACY 1,562,460, RAW 274,050); additional-family prototype (section431_additions.py) and feasibility diagnostics."),
        ("2", "Missingness, calendar and family-coverage audit (coverage amendment frozen before that run read data, but written after aggregate coverage had already been seen)",
         f"11 feature families screened against the 80% floor in each era: {len(meets)} meet it ({', '.join(meets)}); {len(below)} are below it in LEGACY ({', '.join(below)}), all strict-60-return families (LEGACY 37.735%, RAW 82.982%). Family proxies only; verification then pending."),
        ("3", "Implementation audit of 81 outputs per era (35 original, 46 additional)",
         "RAW PASS and LEGACY PASS, 8 of 8 checks each: inventory, formula_all_outputs (independent per-row oracle, synthetic panel), formula_spot_checks, real_train_prefix_invariance, prior_session_isolation, numerical_sanity, deferred_implementations, provider_isolation. Prefix and isolation tests use the 40-session slice method. Phase-A baseline: test_candidates 6 pass; the prototype test_additions.py runs no tests."),
        ("4", "Lookback, minimum valid observations and warmup extracted from the code, compared with the frozen protocol and A2",
         "80 PASS, 0 FAIL, 1 EXCLUDED (overnight_return_open). Before A2 the same comparison gave 35 PASS, 1 FAIL (overnight contradicts the frozen 'No overnight returns') and 45 NO_SPEC. No output reads bars after t."),
        ("5", "Causality and boundary policy P1, with verification",
         "R1 usable at t+1 minute, R2 session reset, R3 no LEGACY/RAW crossing, R4 overnight excluded: all PASS against saved Step 3/4 results. The original one-bar shift test FAILED and is retained, labeled MIS-SPECIFIED (not counted). Replacement test (identical values, available_at = t+2 min, point-in-time replay) PASS on a synthetic panel, a RAW slice and a LEGACY slice."),
        ("6", "TRAIN-only coverage of the 80 detector outputs (descriptive)",
         "Frozen coverage amendment: denominator all TRAIN grid rows per era, 80% floor in each era; numerator = the column's own finite values (user decision). 20 PASS, 60 BELOW, all 60 below in LEGACY only; RAW is at least 82.7% everywhere. No PASS column has a LEGACY year under 80%."),
    ]
    limitations = [
        "60 of the 80 detector outputs are BELOW the 80% coverage floor in LEGACY (every 15-, 30- and 60-minute window output and shock_prior60_mad, lee_mykland_*). Closing this section does not decide whether to drop, keep or re-window them; that is an open model-selection decision.",
        "The coverage amendment is 'post-screening': aggregate coverage had been inspected before it was written. It defines numerators only for 11 families through proxies; using each column's own finite values is an extension chosen by the user. Step 2 family proxies differ from the real windowed columns (for example drawdown proxy 96.9% vs drawdown_15 76.9%, drawdown_60 37.7% in LEGACY). Earlier availability figures in REPORT.md use a different denominator and are not comparable.",
        "Step 3 audited TRAIN spans only (LEGACY 2003-01-02..2018-12-21, RAW 2022-03-07..2024-12-23). The frozen development spans extend to 2022-03-04 (LEGACY) and 2024-12-31 (RAW); the days around the 2022-03-04/2022-03-07 boundary and the evaluation period were never in an audited span. R3 rests on era-separate loading and the first-10-sessions check.",
        "Prefix and isolation tests use a 40-session slice (last 15 sessions compared), not full-era recomputation. Formula checks against the independent oracle ran on one synthetic panel; only spot checks ran on real data. The delay-test replay used 3 rows per dataset, and its value-identity check holds partly by construction because the feature code never reads the availability field.",
        "The 45 outputs added by A2 were specified after implementation and are not ex ante. Their formulas come from section431_additions.py and, for close_location_proxy and lee_mykland_*, were ported from section-4.3.1.py because build_features_4_3_1.py does not exist; lee_mykland_jump60 was added as a fourth output. Two different documents carry the name 'A2' (4.3.1-A2 here and 4.3.1-A2-post-screening for coverage).",
        "The cap '60 prior bars' is defined on return-bars (Step 4 lookback limit 61). A literal cap that counts the reference close as a bar would exclude shock_prior60_mad (frozen) and lee_mykland_*. Amendment 4.3.0-A1 remains an unapproved proposal; its 60-minute lookback and 5-session embargo do not cover the 20-session relative-volume history, and this conflict is unresolved.",
        "overnight_return_open is excluded declaratively (A2, Step 4 check). The audit script still computes it and no detector code exists to enforce the exclusion. The overnight analysis itself is not specified.",
        "LEGACY historical clock semantics and possible centered vendor cleaning remain unresolved; a past-only implementation does not certify vendor causality. Later timing work must report the legacy -1/0/+1 minute sensitivity.",
        "Cumulative-sum features (strict RV, downside, momentum) carry about 1e-13 of absolute floating-point noise that depends on earlier bars in the session; harmless for modelling, formulas unchanged.",
        "The original delay test failed at clock-position edge rows (partial90 at slot W; relative volume after an early close). It was replaced after the failure was seen; the replacement was therefore not set ex ante.",
        "No 2025-2026 period is an unexposed test. The git repository was created in Downloads during Step 3 onward; the frozen documents are copied into frozen_documents/ with hashes verified identical to the originals, which remain where they were.",
    ]
    deferred = ["Which BELOW-floor outputs to keep, drop or re-window", "The overnight analysis and its specification", "Approval or rejection of amendment 4.3.0-A1 and the embargo", "Any detector, scaler or HMM fit", "Legacy timing sensitivity"]

    now = datetime.datetime.now(datetime.timezone.utc)
    ny = pd.Timestamp(now).tz_convert("America/New_York").isoformat()
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    head = git("rev-parse", "HEAD")
    report = dict(status="SECTION_4_3_1_CLOSED", section="4.3.1", closed_utc=now.isoformat(), closed_america_new_york=ny,
                  repo_head_before_closing_commit=head,
                  summary=dict(outputs=81, detector_outputs=80, excluded=EXCLUDED, step4=t4["counts"], coverage=cov["counts"], step3={e: rep[e]["status"] for e in rep}),
                  steps=[dict(step=a, title=b, result=c) for a, b, c in steps],
                  feature_dictionary=dictionary,
                  documents=[dict(name=n, file=p.name, sha256=sha(p), dated=dt, location=loc) for n, p, dt, loc in documents],
                  file_inventory=inventory, known_limitations=limitations, decisions_not_taken=deferred)
    jpath = R / f"section_4_3_1_closing_report_{stamp}.json"
    jpath.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))

    L = [f"# Section 4.3.1 closing report", "", "**SECTION_4_3_1_CLOSED**", "",
         f"Closed {now.isoformat()} UTC ({ny} New York). Repository HEAD before this commit: `{head}`.", "",
         "Closed means the construction and audit of the 4.3.1 features are complete and recorded. It does not settle the open decisions listed at the end.", "",
         "## Steps 1-6", "", "| Step | Scope | Result |", "|---|---|---|"]
    L += [f"| {a} | {b} | {c} |" for a, b, c in steps]
    L += ["", "## Amendments and policies", "", "| Document | Dated | SHA-256 | Location |", "|---|---|---|---|"]
    L += [f"| {n} (`{p.name}`) | {dt} | `{sha(p)}` | {loc} |" for n, p, dt, loc in documents]
    L += ["", "Other hashed records: Step 3 reports, Step 4 table, verification reports, coverage and the diagnosis are listed in the inventory below and in each step's `*_sha256.txt`.", "",
          "## Feature dictionary (80 detector outputs and the excluded one)", "",
          "| Output | Specified by | Lookback (bars / sessions) | Min valid | Warmup | Step 4 | LEGACY % | RAW % | Coverage |", "|---|---|---|---|---|---|---|---|---|"]
    for x in dictionary:
        lp = "-" if x["coverage_LEGACY_pct"] is None else f"{x['coverage_LEGACY_pct']:.3f}"
        rp = "-" if x["coverage_RAW_pct"] is None else f"{x['coverage_RAW_pct']:.3f}"
        L.append(f"| {x['output']} | {x['specified_by']} | {x['lookback_bars']} / {x['lookback_sessions']} | {x['min_valid_obs']} | {x['warmup']} | {x['step4_status']} | {lp} | {rp} | {x['coverage_status'] or 'excluded'} |")
    L += ["", "### Definitions", "", "Frozen protocol (verbatim, `windows_minutes` 5, 10, 15, 30, 60):", ""]
    for key in ("return_1m", "strict", "endpoint_momentum", "partial90", "sampled5", "range", "volume", "shock"):
        L.append(f"- **{key}**: {d[key]}")
    L += ["- **abs_return_1m**: absolute value of return_1m", "", "A2 (w = the window in the output name: 15, 30 or 60; `lee_mykland_*` use 60 prior returns):", ""]
    seen = set()
    for x in a2["specified_outputs"]:
        fam = x["family"]
        if fam in seen and fam != "lee_mykland": continue
        if fam == "lee_mykland":
            L.append(f"- **{x['output']}**: {x['definition']}"); continue
        seen.add(fam)
        L.append(f"- **{x['output'].rsplit('_', 1)[0]}**: {re.sub(r' [(]w=[0-9]+[)]$', '', x['definition'])}")
    L.append(f"- **{EXCLUDED}** (excluded): {dictionary[[x['output'] for x in dictionary].index(EXCLUDED)]['definition']}")
    L += ["", "Cap (A2): a detector feature may use the returns of the 60 bars before t and of bar t itself; Step 4 lookback limit 61. Missing data: no interpolation or fill, NaN is never zero.", "",
          "## Known limitations", ""] + [f"{i}. {t}" for i, t in enumerate(limitations, 1)]
    L += ["", "## Decisions not taken", ""] + [f"- {t}" for t in deferred]
    L += ["", "## SHA-256 inventory of tracked files (before the closing commit)", "", "| Path | SHA-256 |", "|---|---|"] + [f"| {x['path']} | `{x['sha256']}` |" for x in inventory]
    mpath = jpath.with_suffix(".md")
    mpath.write_text("\n".join(L) + "\n", encoding="utf-8")
    side = jpath.with_name(jpath.stem + ".sha256")
    side.write_text(f"{sha(jpath)}  {jpath.name}\n{sha(mpath)}  {mpath.name}\n", encoding="ascii")
    print(jpath.name, "\n", side.read_text())


if __name__ == "__main__":
    main()
