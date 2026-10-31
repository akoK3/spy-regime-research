#!/usr/bin/env python3
"""Final Section 4 closing record (marker SECTION_4_CLOSED). Reads saved results only; refuses to overwrite.
METHODS_LEDGER.md and SECTION4_COMPLETE.md are rebuilt after this record and list it; their hashes are in their own sidecars."""
import json, hashlib, subprocess, datetime
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
R = ROOT / "section431_step3_all_in_one_results"
FZ = ROOT / "frozen_documents"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def one(pattern):
    files = sorted(R.glob(pattern))
    assert len(files) == 1, pattern
    return files[0]


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main():
    assert not list(R.glob("section_4_final_closing_2*.json")), "exists; never overwrite"
    n4, addr = one("note_4_3_N4_2*.json"), one("section_4_3_closing_report_addendum_reaudit_2*.json")
    chk = load(R / "n4_checks.json")
    assert load(addr)["overall"] == "PASS" and all(t[1] == "PASS" for t in chk["table"])
    mat = pd.read_csv(R / "a4_sec4_3_9_frozen_matrix_v2.csv")
    docs = [("Frozen protocol v2", FZ / "protocol_20261029T032641Z.json"), ("Amendment 4.3.0-A1 (approved after use)", FZ / "protocol_amendment_4_3_0_A1_20261029T034121Z.json"), ("Approval of A1", one("approval_4_3_0_A1_2*.json")),
            ("Coverage amendment 4.3.1-A2-post-screening", FZ / "protocol_amendment_431_A2_FROZEN_coverage.json"), ("Amendment 4.3.1-A2", one("amendment_4_3_1_A2_*.json")),
            ("Policy P1 (rule R2 amended by N4 D1)", one("policy_4_3_1_P1_2*.json")), ("Policy addendum P1-A", one("policy_4_3_1_P1_addendum_2*.json")), ("Amendment A3", one("amendment_4_3_A3_2*.json")),
            ("Note N1", one("note_4_3_N1_2*.json")), ("Note N2", one("note_4_3_N2_2*.json")), ("Amendment A4", one("amendment_4_3_A4_2*.json")), ("Amendment A5", one("amendment_4_3_A5_2*.json")),
            ("Note N3", one("note_4_3_N3_2*.json")), ("Note N4", n4), ("Cold audit", ROOT / "cold_audit_20261030.md"), ("Re-audit", ROOT / "reaudit_20261031.md"),
            ("Section 4.3.1 closing report", one("section_4_3_1_closing_report_2*.json")), ("Section 4.3 closing report", one("section_4_3_closing_report_section4_2*.json")),
            ("Addendum: audit disclosures and correction #7", one("section_4_3_closing_report_addendum_audit_2*.json")), ("Addendum: availability check", one("section_4_3_closing_report_addendum_availability_2*.json")),
            ("Addendum: re-audit disclosures and fixes", addr), ("A4 results report", R / "a4_results_report.json"), ("A5 results report", R / "a5_results_report.json"),
            ("4.3.6 yearly median and IQR (113 columns)", R / "a4_sec4_3_6_yearly_median_iqr.csv"), ("4.3.9 frozen matrix, base", R / "a4_sec4_3_9_frozen_matrix.csv"), ("4.3.9 frozen matrix, v2 (warmup corrected)", R / "a4_sec4_3_9_frozen_matrix_v2.csv"),
            ("N4 checks", R / "n4_checks.json")]
    inventory = [dict(path=p, sha256=sha(ROOT / p)) for p in git("ls-files").splitlines()]
    now = datetime.datetime.now(datetime.timezone.utc)
    ny = pd.Timestamp(now).tz_convert("America/New_York").isoformat()
    head = git("rev-parse", "HEAD")
    doc = dict(status="SECTION_4_CLOSED", closed_utc=now.isoformat(), closed_america_new_york=ny, repo_head_before_closing_commit=head,
               scope="Section 4 as recorded in this repository: 4.3.0 to 4.3.9 with amendments A1 to A5 and notes N1 to N4. The 4.1 and 4.2 text was not provided and is a marked placeholder in SECTION4_COMPLETE.md; pre-rebuild results of sections 4.4 to 4.9 are not part of this record.",
               meaning="Closed means the construction, audit, selection runs and corrections are complete and recorded. It does not resolve the open items for Section 5 (ledger section 3), the unconfirmed or inferred points listed below, or the points the re-audit raised that this pass did not address.",
               final_state=dict(pool_columns=int(len(mat)), raw=int((mat.kind == "raw").sum()), adjusted=int((mat.kind == "adjusted").sum()), primary_eligible=int(mat.primary_eligible.sum()),
                                primary_kept=int((mat.primary_outcome == "kept").sum()), raw_sensitivity_kept=int((mat.sensitivity_outcome == "kept").sum()), raw_sensitivity_dropped=int(mat.sensitivity_outcome.str.startswith("dropped").sum())),
               rules_in_force_changed_by_this_pass=["P1 rule R2 is amended by N4 D1: causal past-session baselines are allowed; after the embargo the same rolling past-only rule applies", "A5 G5 (rv10 in place of rv15) is deferred to Section 5 by N4 D2",
                                                  "A1's 'through 2024-12-31' is read as the development span; the training span is the manifest's TRAIN (N4 D3)"],
               fix_results=dict(chk["table"]) if isinstance(chk["table"], dict) else {a: b for a, b in chk["table"]},
               unresolved_or_inferred=["Amihud: LEGACY closes appear dividend-adjusted (inference); Section 5 normalizes Amihud per fold (N3)", "jump_variation_w is still biased upward after the scaling and about half of its values are exactly 0",
                                       "Lee-Mykland flag rate is not controlled under fat tails or on real data", "Selection (4.3.7/4.3.8) was made on all of TRAIN, not inside folds", "The availability assumption is circular; LEGACY clock and vendor cleaning are open",
                                       "The split manifest is a derived artifact and not approved", "re-audit new #8 and #9 were not addressed in this pass"],
               documents=[dict(name=n, file=(p.relative_to(ROOT).as_posix()), sha256=sha(p)) for n, p in docs], file_inventory=inventory)
    jp = R / f"section_4_final_closing_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    jp.write_bytes((json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    L = ["# Section 4 final closing record", "", "**SECTION_4_CLOSED**", "", f"Closed {now.isoformat()} UTC ({ny} New York). Repository HEAD before this commit: `{head}`.", "", f"Scope: {doc['scope']}", "", f"Meaning: {doc['meaning']}", "",
         "## Final state", "", f"Pool {doc['final_state']['pool_columns']} columns ({doc['final_state']['raw']} raw + {doc['final_state']['adjusted']} adjusted); primary-eligible {doc['final_state']['primary_eligible']}, primary kept {doc['final_state']['primary_kept']}; RAW sensitivity kept {doc['final_state']['raw_sensitivity_kept']}, dropped {doc['final_state']['raw_sensitivity_dropped']}.", "",
         "## Rules changed by this pass", ""] + [f"- {x}" for x in doc["rules_in_force_changed_by_this_pass"]] + ["", "## Fix results (N4)", "", "| Fix | Status |", "|---|---|"] + [f"| {a} | {b} |" for a, b in doc["fix_results"].items()] + \
        ["", "## Unresolved or inferred", ""] + [f"- {x}" for x in doc["unresolved_or_inferred"]] + ["", "## Documents (SHA-256)", "", "| Document | File | SHA-256 |", "|---|---|---|"] + [f"| {d['name']} | {d['file']} | `{d['sha256']}` |" for d in doc["documents"]] + \
        ["", "## SHA-256 inventory of tracked files (before the closing commit)", "", "| Path | SHA-256 |", "|---|---|"] + [f"| {x['path']} | `{x['sha256']}` |" for x in inventory]
    mp = jp.with_suffix(".md"); mp.write_text("\n".join(L) + "\n", encoding="utf-8")
    jp.with_name(jp.stem + ".sha256").write_text(f"{sha(jp)}  {jp.name}\n{sha(mp)}  {mp.name}\n", encoding="ascii")
    print(jp.name); print(jp.with_name(jp.stem + ".sha256").read_text())


if __name__ == "__main__":
    main()
