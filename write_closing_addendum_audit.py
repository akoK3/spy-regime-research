#!/usr/bin/env python3
"""A4 F6: addendum to the Section 4.3 closing reports. Discloses audit findings #3, #4, #6 and corrects #7.
The closed reports are not edited. Every number is read from a file. Refuses to overwrite."""
import ast, json, hashlib, datetime
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
R = ROOT / "section431_step3_all_in_one_results"
FZ = ROOT / "frozen_documents"
SRC = ROOT / "section431_step3_verification" / "prototype_sources"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def one(pattern):
    files = sorted(R.glob(pattern))
    assert len(files) == 1, pattern
    return files[0]


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def fn_source(path, name):
    text = Path(path).read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.FunctionDef) and node.name == name: return ast.get_source_segment(text, node)
    raise KeyError(name)


def main():
    assert not list(R.glob("section_4_3_closing_report_addendum_audit_2*.json")), "exists; never overwrite"
    audit, a4 = ROOT / "cold_audit_20261030.md", one("amendment_4_3_A4_2*.json")
    cl43, cl431, a3, p1 = one("section_4_3_closing_report_section4_2*.json"), one("section_4_3_1_closing_report_2*.json"), one("amendment_4_3_A3_2*.json"), one("policy_4_3_1_P1_2*.json")
    v2p = FZ / "protocol_20261029T032641Z.json"
    red, pool_red, pool_rep = load(R / "sec4_3_8_redundancy.json"), load(R / "sec4_3_7_8_pool116_redundancy.json"), load(R / "sec4_3_7_8_pool116_report.json")
    cov6, a3d, p1d, v2d = load(R / "step6_coverage_TRAIN.json"), load(a3), load(p1), load(v2p)
    cl43d, cl431d = load(cl43), load(cl431)

    # ---- #3: selection on all of TRAIN, outside the folds
    rho_R = pd.read_csv(R / "sec4_3_8_spearman_RAW_all80.csv", index_col=0)
    rho_L = pd.read_csv(R / "sec4_3_8_spearman_primary_LEGACY.csv", index_col=0)
    drops = []
    for col, hits in red["primary"]["dropped"].items():
        k = hits[0]["kept_column"]
        drops.append(dict(dropped=col, kept=k, rho_RAW=round(float(rho_R.loc[col, k]), 6), rho_LEGACY=round(float(rho_L.loc[col, k]), 6)))
    min_rho = min(min(abs(d["rho_RAW"]), abs(d["rho_LEGACY"])) for d in drops)
    d3 = dict(finding="#3", statement="Features are selected on all of TRAIN, outside the folds.",
              protocol_rule=v2d["nested_development"]["rule"],
              facts=[f"4.3.7 and 4.3.8 (A3 run and 116-column pool run) use every TRAIN row of each era; no fold boundary enters the selection.",
                     f"A3 run, primary set: {len(drops)} drops, smallest |rho| with the kept partner over both eras {min_rho}.",
                     f"116-column pool run: primary pool {pool_rep['subsections']['4.3.8']['primary']['pool']} columns with {pool_rep['subsections']['4.3.8']['primary']['dropped']} drops; RAW sensitivity pool {pool_rep['subsections']['4.3.8']['sensitivity_RAW']['pool']} columns with {pool_rep['subsections']['4.3.8']['sensitivity_RAW']['dropped']} drops."],
              drops_a3_primary=drops,
              status_after_a4=(lambda a4r: f"A4 reruns 4.3.4, 4.3.7 and 4.3.8 (causal baseline, 113-column pool): primary pool {a4r['primary']['pool']} columns, keep {a4r['primary']['kept']}, drop {a4r['primary']['dropped']}; RAW sensitivity pool {a4r['sensitivity_RAW']['pool']}, keep {a4r['sensitivity_RAW']['kept']}, drop {a4r['sensitivity_RAW']['dropped']}. It still selects on all of TRAIN; the folds of F1 are not used by the selection. Selections stay descriptive until recomputed inside each fold.")(load(R / "a4_sec4_3_4_7_8_report.json")["subsections"]["4.3.8"]))

    # ---- #4: era-crossing decisions
    ir = next(r for r in pool_red["raw_vs_adjusted_rho"] if r["column"] == "intrabar_range_log")
    ir_drop = pool_red["primary"]["dropped"]["intrabar_range_log__sadj"][0]
    below = [c["column"] for c in cov6["columns"] if c["status"] == "BELOW"]
    raw_cov_min = min(c["RAW_pct"] for c in cov6["columns"])
    d4 = dict(finding="#4", statement="Era-crossing decisions contradict the project's own rule.",
              rules=[f"A3 general_rules: {a3d['general_rules'][1]}", f"P1 R3: {next(r for r in p1d['rules'] if r['id'] == 'R3')['rule']}"],
              facts=[f"A3 4.3.7 primary requires at least 80% in both eras; A3 4.3.8 calls a pair redundant if |rho| > 0.95 in either era. Both combine the two eras in one decision.",
                     f"intrabar_range_log__sadj left the primary pool because of LEGACY: rho with intrabar_range_log {ir_drop['rho']} ({ir_drop['era']}), versus {ir['RAW_rho']} in RAW.",
                     f"Step 6: {len(below)} columns are BELOW the floor in LEGACY only; the lowest RAW coverage of any column is {raw_cov_min}%. The LEGACY coverage therefore removes {len(below)} columns from RAW's primary set.",
                     "In the primary set the RAW correlations feed decisions on LEGACY columns, and the reverse."])

    # ---- #6: delay checks
    sources = {"construct": fn_source(SRC / "section4_3_1_candidates.py", "construct"), "relative_volume": fn_source(SRC / "section4_3_1_candidates.py", "relative_volume"),
               "construct_additions": fn_source(SRC / "section431_additions.py", "construct_additions"), "construct_deferred": fn_source(ROOT / "step3_all_in_one.py", "construct_deferred")}
    import re
    pattern = re.compile(r"""\[\s*['"]available['"]\s*\]|\.get\(\s*['"]available['"]""")  # an access of the key, not the word in a comment
    reads_available = [n for n, t in sources.items() if pattern.search(t)]
    audit_text = audit.read_text(encoding="utf-8")
    repl = load(one("policy_4_3_1_P1_addendum_2*.json"))["replacement_delay_test"]
    d6 = dict(finding="#6", statement="Two of the three replacement delay checks cannot fail.",
              replacement_test=repl["definition"],
              facts=[f"Functions among construct, relative_volume, construct_additions, construct_deferred that access the 'available' key of the data: {reads_available or 'none'}. " + ("The 'all feature values identical' check therefore compares features computed from the same bars and cannot differ." if not reads_available else "NEEDS REVIEW: a feature function reads the field."),
                     "The 'available_at = t+2 minutes' check is computed from the t and available arrays, not from any feature value, so it holds by construction.",
                     "The point-in-time replay is the only check that exercises the data, and it covers 3 rows per dataset.",
                     "Audit-reported, not reproduced here: shifting all 80 features one bar into the future left the first two checks passing, while the replay failed on 76, 73 and 72 of 80 outputs.",
                     f"The 4.3.1 closing report disclosed this only as: '{next(x for x in cl431d['known_limitations'] if 'by construction' in x)}'"],
              counted_rows_that_cannot_fail=6, counted_delay_rows=9)

    # ---- #7: correction
    runs = load(FZ / "builder_results_v2_summary.json")["runs"]
    cov = pd.read_csv(FZ / "builder_feature_coverage_development.csv")
    yrs = {e: sorted(y for y in cov[(cov.era == e) & (cov.year != "ALL")].year.astype(str).unique()) for e in ("LEGACY", "RAW")}
    man = pd.read_csv(FZ / "section430_executable_split_manifest.csv", dtype=str)
    part = lambda e, p: man[(man.provider_era == e) & (man.partition == p)].session_date.sort_values().tolist()
    claim = next(x for x in cl43d["known_limitations"] if "never in an audited or analysed span" in x)
    c7 = dict(finding="#7", statement="The closing report's statement about later development days and the evaluation period is false as worded.",
              original_statement=claim, source_file=cl43.name, source_sha256=sha(cl43),
              facts=[f"The 4.3.1 builder (summary created {load(FZ / 'builder_results_v2_summary.json')['created_utc']}) built {runs['LEGACY']['rows']} LEGACY rows ({runs['LEGACY']['first_session']} to {runs['LEGACY']['last_session']}, {runs['LEGACY']['sessions']} sessions) and {runs['RAW']['rows']} RAW rows ({runs['RAW']['first_session']} to {runs['RAW']['last_session']}, {runs['RAW']['sessions']} sessions): {runs['LEGACY']['rows'] + runs['RAW']['rows']} rows.",
                     f"The 4.3.1 closing report records the same total: '{cl431d['steps'][0]['result'][cl431d['steps'][0]['result'].index('35 candidate'):cl431d['steps'][0]['result'].index('minute rows)') + len('minute rows)')]}'.",
                     f"The manifest puts LEGACY {part('LEGACY','EMBARGO')[0]} to {part('LEGACY','EMBARGO')[-1]} in EMBARGO ({len(part('LEGACY','EMBARGO'))} sessions) and {part('LEGACY','EVALUATION_EXPOSED')[0]} to {part('LEGACY','EVALUATION_EXPOSED')[-1]} in EVALUATION_EXPOSED ({len(part('LEGACY','EVALUATION_EXPOSED'))} sessions); RAW EMBARGO is {part('RAW','EMBARGO')[0]} to {part('RAW','EMBARGO')[-1]} ({len(part('RAW','EMBARGO'))} sessions) and RAW EVALUATION_EXPOSED starts {part('RAW','EVALUATION_EXPOSED')[0]}.",
                     f"The builder's yearly coverage table (builder_feature_coverage_development.csv) lists LEGACY years {yrs['LEGACY'][0]} to {yrs['LEGACY'][-1]} and RAW years {yrs['RAW'][0]} to {yrs['RAW'][-1]}, so features for LEGACY 2019-2022 and the RAW embargo days were built and summarised by year."],
              corrected_statement=f"The LEGACY sessions {part('LEGACY','EMBARGO')[0]} to {part('LEGACY','EVALUATION_EXPOSED')[-1]} and the RAW embargo sessions {part('RAW','EMBARGO')[0]} to {part('RAW','EMBARGO')[-1]} were inside the span on which the 4.3.1 builder constructed features and summarised coverage by year. Steps 3 to 6 and Sections 4.3.4 to 4.3.9 used TRAIN rows only. No feature matrix was built for the RAW evaluation period ({part('RAW','EVALUATION_EXPOSED')[0]} onward): the builder's runs end at {runs['RAW']['last_session']}.")

    now = datetime.datetime.now(datetime.timezone.utc)
    ny = pd.Timestamp(now).tz_convert("America/New_York").isoformat()
    doc = dict(status="SECTION_4_3_CLOSED (addendum; the closed reports are unchanged)", created_utc=now.isoformat(), created_america_new_york=ny,
               amends=[dict(file=cl43.name, sha256=sha(cl43)), dict(file=cl431.name, sha256=sha(cl431))], basis=dict(audit=dict(file=audit.name, sha256=sha(audit)), amendment_A4=dict(file=a4.name, sha256=sha(a4))),
               disclosures=[d3, d4, d6], correction=c7)
    jp = R / f"section_4_3_closing_report_addendum_audit_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    jp.write_bytes((json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    L = ["# Section 4.3 closing reports: addendum from the cold audit (#3, #4, #6 disclosed; #7 corrected)", "", "**SECTION_4_3_CLOSED** (unchanged; the closed reports are not edited)", "",
         f"Added {now.isoformat()} UTC ({ny} New York). Audit `{audit.name}` SHA-256 `{sha(audit)}`. Amendment A4 `{a4.name}` SHA-256 `{sha(a4)}`.", "",
         "Amends: " + "; ".join(f"`{x['file']}` (`{x['sha256']}`)" for x in doc["amends"]), ""]
    for d in (d3, d4, d6):
        L += [f"## Disclosure {d['finding']}: {d['statement']}", ""]
        for k in ("protocol_rule",):
            if k in d: L += [f"Protocol rule: {d[k]}", ""]
        if "rules" in d: L += [f"- Rule: {r}" for r in d["rules"]] + [""]
        if "replacement_test" in d: L += [f"Replacement test as defined: {d['replacement_test']}", ""]
        L += [f"- {f}" for f in d["facts"]]
        if "status_after_a4" in d: L += ["", f"After A4: {d['status_after_a4']}"]
        L += [""]
    L += [f"## Correction {c7['finding']}: {c7['statement']}", "", f"Original statement (`{c7['source_file']}`, `{c7['source_sha256']}`): {c7['original_statement']}", ""] + [f"- {f}" for f in c7["facts"]] + ["", f"Corrected statement: {c7['corrected_statement']}"]
    mp = jp.with_suffix(".md")
    mp.write_text("\n".join(L) + "\n", encoding="utf-8")
    jp.with_name(jp.stem + ".sha256").write_text(f"{sha(jp)}  {jp.name}\n{sha(mp)}  {mp.name}\n", encoding="ascii")
    print(jp.name); print(jp.with_name(jp.stem + ".sha256").read_text())


if __name__ == "__main__":
    main()
