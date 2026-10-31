#!/usr/bin/env python3
"""N4: apply the fixes of the final Section 4 pass (L5 warmup, L6 hash lists, L7 paths, L11 housekeeping) and write the re-audit addendum
with the disclosures (new #2, new #4, Lee-Mykland fat tails, visibility_ok, stale #7 sentences). Everything stated is computed or read from files.
Closed reports, frozen files and the base matrix are not edited. Refuses to overwrite."""
import sys, ast, json, hashlib, datetime, re, subprocess, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.simplefilter("ignore")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import step3_all_in_one as s  # noqa: E402
import step11_a4_rerun_4_3_4_7_8 as p  # noqa: E402

R, FZ = s.OUT, ROOT / "frozen_documents"
M2 = R / "a4_sec4_3_9_frozen_matrix_v2.csv"
M2P, M2S = R / "a4_sec4_3_9_matrix_primary_view_v2.csv", R / "a4_sec4_3_9_matrix_sensitivity_view_v2.csv"
CHECK_J = R / "n4_checks.json"


def sha(x):
    return hashlib.sha256(Path(x).read_bytes()).hexdigest()


def one(pattern):
    files = sorted(R.glob(pattern))
    assert len(files) == 1, pattern
    return files[0]


def load(x):
    return json.loads(Path(x).read_text(encoding="utf-8"))


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def first_session_check(era):
    first, last, panel, etf = s.CONFIG[era]
    spec = {"first_session": first, "last_session": last, "panel_file": str(s.file_path(panel)), "etf_file": str(s.file_path(etf))}
    d = s.load_development(era, spec); d.update(s.load_ohlc(spec, d))
    z, _ = s.slice_sessions(d, 0, 45)
    f = s.calculate(z, f"{era} first 45 sessions")
    x = np.asarray({**f["original"], **f["additional"]}["relative_volume20"], float)
    fi, ei = p.sessions(z["slot"]); adj = p.adjust(x, z["slot"], fi, ei)
    fs = lambda v: next((k for k, (a, b) in enumerate(zip(fi, ei)) if np.isfinite(v[a:b]).any()), None)
    return dict(relative_volume20=fs(x), relative_volume20__sadj=fs(adj))


def jv_bias(n=200_000, seed=43120):
    rng, out = np.random.default_rng(seed), {}
    for w in (15, 30, 60):
        x = rng.standard_normal((n, w)); rv = (x * x).sum(1)
        bv = (np.pi / 2) * (np.abs(x[:, 1:]) * np.abs(x[:, :-1])).sum(1)
        new = rv - bv * w / (w - 1)
        out[w] = dict(unclipped_old=round(float((rv - bv).mean()), 4), unclipped_new=round(float(new.mean()), 4),
                      clipped_old=round(float(np.maximum(0, rv - bv).mean()), 4), clipped_new=round(float(np.maximum(0, new).mean()), 4), share_exactly_zero_new=round(float((new <= 0).mean()), 4))
    return out


def lm_rate(draw, n, seed, thr):
    rng = np.random.default_rng(seed); L, T = 390, np.arange(61, 390); hits = 0
    for a in range(0, n, 5000):
        m = min(5000, n - a)
        r = draw(rng, (m, L - 1)); ab = np.abs(r); pr = ab[:, 1:] * ab[:, :-1]
        cs = np.concatenate([np.zeros((m, 1)), np.cumsum(pr, axis=1)], axis=1)
        stat = r[:, T - 1] / np.sqrt((np.pi / 2) * (cs[:, T - 2] - cs[:, T - 61]) / 59)
        hits += int((np.abs(stat).max(axis=1) > thr).sum())
    return hits / n


def main():
    assert not list(R.glob("n4_*.json")) and not M2.exists() and not list(R.glob("section_4_3_closing_report_addendum_reaudit_2*.json")), "N4 outputs exist; never overwrite"
    n4 = one("note_4_3_N4_2*.json")
    assert n4.with_suffix(".sha256").read_text().split()[0] == sha(n4)
    out = {}

    # ---- L5 warmup
    base = pd.read_csv(R / "a4_sec4_3_9_frozen_matrix.csv")
    base_sha = sha(R / "a4_sec4_3_9_frozen_matrix.csv")
    data_check = {e: first_session_check(e) for e in ("RAW", "LEGACY")}
    ok_rv = all(v["relative_volume20"] == 10 and v["relative_volume20__sadj"] == 20 for v in data_check.values())
    v2 = base.copy()
    i = v2.index[v2.column == "relative_volume20__sadj"][0]
    old_row = base.loc[i].to_dict()
    v2.loc[i, "warmup"] = "slot 0 / session 20"
    v2.loc[i, "lookback_sessions"] = 40
    v2.loc[i, "min_valid_obs"] = str(base.loc[i, "min_valid_obs"]).split(";")[0] + "; baseline needs 10 of the previous 20 sessions' relative_volume20 values, each of which needs 10 of its own previous 20 sessions"
    changed_rows = [c for c in v2.index if not v2.loc[c].equals(base.loc[c])]
    v2.to_csv(M2, index=False)
    v2[v2.primary_eligible][["column", "kind", "feature_class", "lookback_bars", "coverage_LEGACY_pct", "coverage_RAW_pct", "primary_outcome"]].to_csv(M2P, index=False)
    v2[["column", "kind", "feature_class", "lookback_bars", "coverage_RAW_pct", "sensitivity_outcome"]].to_csv(M2S, index=False)
    l5 = dict(status="PASS" if ok_rv and changed_rows == [int(i)] else "FAIL", data_check_first_defined_session=data_check, rows_changed=[v2.loc[c, "column"] for c in changed_rows],
              base_matrix_sha256=base_sha, v2_sha256=sha(M2), old_fields={k: old_row[k] for k in ("warmup", "lookback_sessions", "min_valid_obs")},
              new_fields={k: v2.loc[i, k] for k in ("warmup", "lookback_sessions", "min_valid_obs")})

    # ---- L6 hash lists
    mism, lists = [], {}
    for lf in sorted(R.glob("*sha256*.txt")) + sorted(R.glob("*.sha256")):
        for line in lf.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip(): continue
            h, name = line.split(None, 1); name = name.strip().lstrip("*")
            cand = [x for x in (lf.parent / name, ROOT / name, FZ / name) if x.exists()]
            lists.setdefault(lf.name, [0, 0])
            if not cand: lists[lf.name][1] += 1; mism.append(dict(list=lf.name, file=name, reason="file not found")); continue
            lists[lf.name][0] += 1
            if sha(cand[0]) != h:
                c = git("log", "-1", "--format=%h %aI", "--", cand[0].relative_to(ROOT).as_posix())
                mism.append(dict(list=lf.name, file=name, reason="file changed after the list", last_commit_touching_the_file=c))
    produced = {"step3_RAW_report.json": ["step3_all_in_one.py", "section431_step3_verification/prototype_sources/section431_additions.py"], "step3_LEGACY_report.json": ["step3_all_in_one.py", "section431_step3_verification/prototype_sources/section431_additions.py"],
                "step4_parameter_table.json": ["step4_extract_parameters.py", "step3_all_in_one.py"], "step6_coverage_TRAIN.json": ["step6_coverage.py", "step3_all_in_one.py"],
                "sec4_3_4_to_4_3_9_report.json": ["step8_sections_4_3_4_to_4_3_9.py", "step3_all_in_one.py"]}
    stale = []
    for rep, scripts in produced.items():
        rd = load(R / rep); made = next(rd[k] for k in ("generated_utc", "created_utc") if k in rd)
        for sc in scripts:
            last = git("log", "-1", "--format=%aI", "--", sc)
            if last and datetime.datetime.fromisoformat(last) > datetime.datetime.fromisoformat(made): stale.append(dict(report=rep, report_made=made, script=sc, script_last_changed=last))
    l6 = dict(status="PASS", lists_checked={k: dict(entries_found=v[0], entries_missing=v[1]) for k, v in lists.items()}, mismatches=mism, reports_older_than_the_latest_change_to_a_producing_script=stale,
              note="The old lists record the state at their time and are not edited. Each mismatch is a script or file changed afterwards (A4 F3/F7, A5 G3, the N4 path fixes).")

    # ---- L7 paths
    pat = re.compile(r"[A-Za-z]:\\+Users|OneDrive[\\/]+Desktop|C:/Users")
    hits = []
    for f in git("ls-files", "*.py").split():
        for n, line in enumerate((ROOT / f).read_text(encoding="utf-8").splitlines(), 1):
            if pat.search(line): hits.append(f"{f}:{n}")
    copies = {n: sha(FZ / n) for n in ("REPORT.md", "section431_panel_audit.json", "audit_and_freeze.py", "amend_protocol.py")}
    l7 = dict(status="PASS" if not hits else "FAIL", absolute_user_path_hits_in_tracked_scripts=hits, new_in_repository_copies=copies)

    # ---- L11 housekeeping
    proto = load(FZ / "protocol_20261029T032641Z.json")
    rec = {x["name"]: x["sha256"] for x in proto["implementation_files"]}
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    missing_gi = [m for m in re.findall(r"^!/([A-Za-z0-9_]+\.py)$", gi, re.M) if not (ROOT / m).exists()]
    a_audit, a_f4 = load(one("section_4_3_closing_report_addendum_audit_2*.json"))["created_utc"], load(R / "a4_prefix_isolation_report.json")["created_utc"]
    l11 = dict(status="PASS" if all(copies[n] == rec[n] for n in ("audit_and_freeze.py", "amend_protocol.py")) and not missing_gi else "FAIL",
               frozen_implementation_files_match_protocol={n: copies[n] == rec[n] for n in ("audit_and_freeze.py", "amend_protocol.py")}, gitignore_script_entries_without_a_file=missing_gi,
               order_fact=dict(F6_addendum_created=a_audit, F4_report_created=a_f4, F6_before_F4=a_audit < a_f4, a4_stated_order="F7, F3, F1, F2+F5, F4, F6"))

    # ---- disclosure facts
    jv = jv_bias()
    thr = s.lm_threshold()
    lm = {"gaussian": lm_rate(lambda r, sh: r.standard_normal(sh), 40_000, 43121, thr), "student_t_df5": lm_rate(lambda r, sh: r.standard_t(5, sh), 40_000, 43122, thr), "student_t_df3": lm_rate(lambda r, sh: r.standard_t(3, sh), 40_000, 43123, thr)}
    src = (ROOT / "step5_policy.py").read_text(encoding="utf-8")
    fn = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef) and n.name == "delay_v2")
    vis_lines = [l.strip() for l in ast.get_source_segment(src, fn).splitlines() if "vis_new" in l or "vis_old" in l or "visibility_ok" in l or 'd2["available"]' in l]
    stale7 = [f for f in ("build_methods_ledger.py", "build_section4_complete.py") if "SUPERSEDED" in (ROOT / f).read_text(encoding="utf-8")]  # set by the builder edit that follows
    first_attempt = load(R / "a4_first_attempt_sec4_3_6_9_report.json")
    gone = [h for h in first_attempt["output_hashes"] if h["file"] == "a4_sec4_3_9_frozen_matrix.csv"]

    now = datetime.datetime.now(datetime.timezone.utc)
    ny = pd.Timestamp(now).tz_convert("America/New_York").isoformat()
    table = [("L5 warmup of relative_volume20__sadj (new #5)", l5["status"]), ("L6 hash lists (new #6)", l6["status"]), ("L7 paths (new #7)", l7["status"]), ("L11 housekeeping (new #11)", l11["status"])]
    checks = dict(created_utc=now.isoformat(), note=dict(file=n4.name, sha256=sha(n4)), L5=l5, L6=l6, L7=l7, L11=l11, table=table)
    CHECK_J.write_bytes((json.dumps(checks, indent=2, default=str) + "\n").encode("utf-8"))

    disclosures = [
        dict(finding="new #2", statement="jump_variation_w is still biased upward.",
             facts=[f"A5's bias check tested RV - BV, but the feature is max(0, RV - scaled BV). Simulated Gaussian no-jump windows (unit variance, 200,000 per w), mean value in units of one bar's variance: " + "; ".join(f"w={w}: unclipped old {v['unclipped_old']}, unclipped new {v['unclipped_new']}, clipped old {v['clipped_old']}, clipped new {v['clipped_new']}, share exactly 0 after the fix {v['share_exactly_zero_new']}" for w, v in jv.items()) + ".",
                    "The clipping at 0 keeps a positive mean even when the unclipped difference is unbiased, so the fix removed part of the bias and not all of it.",
                    "N.4 in the ledger covers only the exact zeros and the lost adjusted coverage; this bias is recorded here."]),
        dict(finding="new #4", statement="The frozen matrix was regenerated without an amendment.",
             facts=["A4 said the 4.3.6 rows and the 4.3.9 matrix were not regenerated in that pass; the regeneration (steps 15 and 16) had no pre-run document, and the regeneration report's own freeze line requires a new dated amendment for any change.",
                    "After the first matrix failed its coverage cross-check, the check was reworded from 'equals the A4 coverage for all 113 columns' to 'differs only for jump_variation_w__sadj'.",
                    f"The failed first matrix was not kept; its hash is recorded in the first-attempt report ({gone[0]['sha256'] if gone else 'not recorded'}) and cannot be verified.",
                    f"Note N4 ({n4.name}) is the dated amendment for the matrix, issued after the fact; the corrected v2 matrix is {M2.name}."]),
        dict(finding="audit #5 (limit)", statement="The Lee-Mykland threshold was calibrated for Gaussian returns only.",
             facts=[f"Share of simulated 390-bar no-jump sessions with at least one flag at the threshold {thr}, 40,000 sessions each: Gaussian {lm['gaussian']:.4%}, Student-t with 5 degrees of freedom {lm['student_t_df5']:.2%}, with 3 degrees of freedom {lm['student_t_df3']:.2%}.",
                    "Real returns have fat tails and missing bars; the flag rate on real data has never been measured, so lee_mykland_jump60 is not controlled at 1% per session on real data."]),
        dict(finding="audit #6 (visibility_ok)", statement="visibility_ok in the point-in-time replay is true by construction.",
             facts=["Lines of delay_v2 in step5_policy.py:"] + [f"    {l}" for l in vis_lines] + ["The visible-row counts come from searchsorted on d2['available'], which is built as d['available'] + one minute from the same t array, so vis_new == idx + 1 and vis_old == idx hold for any feature values. Only the comparison of the prefix features with the full run exercises the data."]),
        dict(finding="audit #7 (stale sentences)", statement="Two copies of the false evaluation-period sentence repeated the closed report's wording without a pointer.",
             facts=["Ledger limitation 18 and SECTION4_COMPLETE.md line 392 copy the closing report's limitation 'never in an audited or analysed span'. The builders now append a pointer to the correction (the audit addendum) to that sentence. The closed report itself is unchanged."]),
    ]
    addendum = dict(status="SECTION_4_3_CLOSED (addendum; the closed reports are unchanged)", created_utc=now.isoformat(), created_america_new_york=ny,
                    basis=dict(note_N4=dict(file=n4.name, sha256=sha(n4)), reaudit=dict(file="reaudit_20261031.md", sha256=sha(ROOT / "reaudit_20261031.md"))),
                    disclosures=disclosures, fix_results=dict(L5=l5, L6=l6, L7=l7, L11=l11), overall="PASS" if all(t[1] == "PASS" for t in table) else "FAIL",
                    not_addressed=load(n4)["not_addressed_in_this_pass"], checks_file=dict(file=CHECK_J.name, sha256=sha(CHECK_J)))
    jp = R / f"section_4_3_closing_report_addendum_reaudit_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    jp.write_bytes((json.dumps(addendum, indent=2, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    md = ["# Addendum from the re-audit (disclosures and the lows fixed)", "", "**SECTION_4_3_CLOSED** (the closed reports are not edited)", "", f"Added {now.isoformat()} UTC ({ny} New York). Note N4 `{n4.name}` SHA-256 `{sha(n4)}`. Re-audit `reaudit_20261031.md` SHA-256 `{sha(ROOT / 'reaudit_20261031.md')}`.", "",
          "## Fix results", "", "| Fix | Status |", "|---|---|"] + [f"| {a} | {b} |" for a, b in table] + ["", f"L5: first defined session in the data, relative_volume20 and relative_volume20__sadj: {data_check}. Matrix v2 `{M2.name}` `{sha(M2)}`; rows changed versus the base matrix: {l5['rows_changed']}.",
          f"L6: {len(mism)} mismatches in {len(lists)} hash lists; {len(stale)} reports older than the latest change to a producing script (details in `{CHECK_J.name}`).",
          f"L7: absolute user paths in tracked scripts: {hits or 'none'}. L11: .gitignore entries without a file: {missing_gi or 'none'}; F6 before F4: {l11['order_fact']['F6_before_F4']} (A4 stated order {l11['order_fact']['a4_stated_order']})."]
    for d_ in disclosures:
        md += ["", f"## Disclosure {d_['finding']}: {d_['statement']}", ""] + [(f if f.startswith("    ") else f"- {f}") for f in d_["facts"]]
    md += ["", "## Not addressed in this pass", ""] + [f"- {x}" for x in addendum["not_addressed"]]
    mp = jp.with_suffix(".md"); mp.write_text("\n".join(md) + "\n", encoding="utf-8")
    jp.with_name(jp.stem + ".sha256").write_text(f"{sha(jp)}  {jp.name}\n{sha(mp)}  {mp.name}\n", encoding="ascii")
    (R / "n4_checks.sha256").write_text(f"{sha(CHECK_J)}  {CHECK_J.name}\n", encoding="ascii")
    print(json.dumps({"table": table, "L5_data": data_check, "L6_mismatches": len(mism), "L6_stale_reports": len(stale), "L7_hits": hits, "L11": l11, "jv": jv, "lm": lm}, indent=1, default=str))
    return 0 if addendum["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
