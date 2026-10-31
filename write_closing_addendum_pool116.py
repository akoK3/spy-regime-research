#!/usr/bin/env python3
"""Addendum to the Section 4.3 closing report: 4.3.7/4.3.8 on the 116-column pool. The closed report is not edited."""
import json, hashlib, datetime
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
R = ROOT / "section431_step3_all_in_one_results"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def one(pattern):
    files = sorted(R.glob(pattern))
    assert len(files) == 1, pattern
    return files[0]


def main():
    assert not list(R.glob("section_4_3_closing_report_addendum_pool116_2*.json")), "exists; never overwrite"
    closing = one("section_4_3_closing_report_section4_2*.json")
    n1, n2 = one("note_4_3_N1_2*.json"), one("note_4_3_N2_2*.json")
    rep = json.loads((R / "sec4_3_7_8_pool116_report.json").read_text(encoding="utf-8"))
    red = json.loads((R / "sec4_3_7_8_pool116_redundancy.json").read_text(encoding="utf-8"))
    assert rep["overall"] == "PASS"
    p, s = rep["subsections"]["4.3.8"]["primary"], rep["subsections"]["4.3.8"]["sensitivity_RAW"]
    adj_kept_s = [c for c in red["sensitivity_RAW"]["kept"] if c.endswith("__sadj")]
    adj_kept_p = [c for c in red["primary"]["kept"] if c.endswith("__sadj")]
    rho = {r["column"]: r for r in red["raw_vs_adjusted_rho"]}
    near = sorted((r["RAW_rho"], r["column"]) for r in red["raw_vs_adjusted_rho"] if 0.94 <= r["RAW_rho"] <= 0.96)
    now = datetime.datetime.now(datetime.timezone.utc)
    ny = pd.Timestamp(now).tz_convert("America/New_York").isoformat()
    limitations = [
        f"Eligibility: every adjusted column has its raw column's coverage in both eras (check PASS), so the primary pool is 30 columns: the 20 raw plus {len([c for c in red['primary']['priority_order'] if c.endswith('__sadj')])} adjusted counterparts of the primary scale features.",
        "The tie-break position of the adjusted columns (80-115, raw wins ties) is the only element not in A3. It was decided by the repository owner, and it decides which member of a redundant raw/adjusted pair is kept.",
        f"Raw/adjusted correlations in RAW sit close to the 0.95 threshold for many pairs ({len(near)} of 36 lie between 0.94 and 0.96), so which adjusted columns survive depends on the threshold. Adjusted columns survive mainly for seasonally strong volume-type features.",
        "Same TRAIN-only scope, medians and Spearman definition as the A3 run; the A3 limitations in the closing report remain in force.",
    ]
    doc = dict(status="SECTION_4_3_CLOSED (addendum; the closing report is unchanged)", created_utc=now.isoformat(), created_america_new_york=ny,
               amends=dict(closing_report=closing.name, closing_report_sha256=sha(closing), item="'Decisions not taken': 'Redundancy and eligibility rules for the 116-column pool' is now done under note N2"),
               rule=dict(N1=dict(file=n1.name, sha256=sha(n1)), N2=dict(file=n2.name, sha256=sha(n2)), statement="A3's 4.3.7 and 4.3.8 rules unchanged, applied to the 116-column pool (80 raw + 36 adjusted); tie-break position of adjusted columns per N2."),
               results=dict(status_4_3_7=rep["subsections"]["4.3.7"]["status"], status_4_3_8=rep["subsections"]["4.3.8"]["status"],
                            primary=dict(pool=p["pool"], kept=p["kept"], dropped=p["dropped"], kept_split=p["kept_split"], dropped_split=p["dropped_split"], adjusted_kept=adj_kept_p),
                            sensitivity_RAW=dict(pool=s["pool"], kept=s["kept"], dropped=s["dropped"], kept_split=s["kept_split"], dropped_split=s["dropped_split"], adjusted_kept=adj_kept_s)),
               raw_vs_adjusted_rho=red["raw_vs_adjusted_rho"], known_limitations=limitations, output_hashes=rep["output_hashes"] + [dict(label="report", file="sec4_3_7_8_pool116_report.json", sha256=sha(R / "sec4_3_7_8_pool116_report.json"))])
    jp = R / f"section_4_3_closing_report_addendum_pool116_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    jp.write_bytes((json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    L = ["# Section 4.3 closing report: addendum (116-column pool)", "", "**SECTION_4_3_CLOSED** (unchanged; this adds results, it does not reopen the section)", "",
         f"Added {now.isoformat()} UTC ({ny} New York). The closing report `{closing.name}` (SHA-256 `{sha(closing)}`) is not edited.", "",
         f"A3's 4.3.7 and 4.3.8 rules, unchanged, applied to the 116-column pool under note N2 (`{n2.name}`, SHA-256 `{sha(n2)}`), which was committed before the run. 4.3.7: {rep['subsections']['4.3.7']['status']}. 4.3.8: {rep['subsections']['4.3.8']['status']}.", "",
         "| Set | Pool | Kept | Dropped | Kept (raw / adjusted) | Dropped (raw / adjusted) |", "|---|---|---|---|---|---|",
         f"| Primary | {p['pool']} | {p['kept']} | {p['dropped']} | {p['kept_split']['raw']} / {p['kept_split']['adjusted']} | {p['dropped_split']['raw']} / {p['dropped_split']['adjusted']} |",
         f"| RAW sensitivity | {s['pool']} | {s['kept']} | {s['dropped']} | {s['kept_split']['raw']} / {s['kept_split']['adjusted']} | {s['dropped_split']['raw']} / {s['dropped_split']['adjusted']} |", "",
         f"Adjusted columns kept in the primary set: {', '.join(adj_kept_p) or 'none'}. In the RAW sensitivity set: {', '.join(adj_kept_s) or 'none'}.", "",
         "## Known limitations added", ""] + [f"{i}. {x}" for i, x in enumerate(limitations, 1)]
    L += ["", "## Output hashes (SHA-256)", "", "| Output | File | SHA-256 |", "|---|---|---|"] + [f"| {h['label']} | {h['file']} | `{h['sha256']}` |" for h in doc["output_hashes"]]
    mp = jp.with_suffix(".md")
    mp.write_text("\n".join(L) + "\n", encoding="utf-8")
    jp.with_name(jp.stem + ".sha256").write_text(f"{sha(jp)}  {jp.name}\n{sha(mp)}  {mp.name}\n", encoding="ascii")
    print(jp.name); print(jp.with_name(jp.stem + ".sha256").read_text())


if __name__ == "__main__":
    main()
