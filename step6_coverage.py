#!/usr/bin/env python3
"""Step 6: TRAIN-only coverage of the 80 detector outputs, descriptive only.

Definition (frozen amendment 4.3.1-A2-post-screening, protocol_amendment_431_A2_FROZEN.json):
  denominator = all frozen TRAIN canonical minute-grid rows per era, including unavailable bars and session openings
  floor       = 80% in EACH era; percentages rounded to 3 decimals as in the Step 2 script
  numerator   = TRAIN rows where the column is finite (chosen by the user: the amendment defines numerators only for
                11 families through proxies, which do not cover all 80 columns)
Nothing here changes a threshold, formula or classification.
"""
import sys, json, hashlib, datetime
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import step3_all_in_one as s  # noqa: E402

OUT = s.OUT
AMEND = ROOT / "section431_step2_final_audit" / "protocol_amendment_431_A2_FROZEN.json"
EXCLUDED = "overnight_return_open"
TRAIN_ROWS = {"LEGACY": 1562460, "RAW": 274050}  # section431_panel_audit.json train_rows


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def era_counts(era):
    first, last, panel, etf = s.CONFIG[era]
    spec = {"first_session": first, "last_session": last, "panel_file": str(s.file_path(panel)), "etf_file": str(s.file_path(etf))}
    d = s.load_development(era, spec)
    d.update(s.load_ohlc(spec, d))
    assert len(d["r"]) == TRAIN_ROWS[era], f"{era}: {len(d['r'])} TRAIN rows, expected {TRAIN_ROWS[era]}"
    f = s.calculate(d, f"{era} coverage")
    cols = {**f["original"], **f["additional"]}
    years = np.array([x[:4] for x in d["day"]])
    ys = sorted(set(years.tolist()))
    yi = np.searchsorted(ys, years)
    rows_by_year = np.bincount(yi, minlength=len(ys))
    out = {}
    for name, v in cols.items():
        if name == EXCLUDED: continue
        fin = np.isfinite(np.asarray(v, float))
        out[name] = dict(finite=int(fin.sum()), by_year=np.bincount(yi, weights=fin, minlength=len(ys)).astype(int).tolist())
    return dict(rows=len(d["r"]), years=ys, rows_by_year=rows_by_year.tolist(), columns=out)


def main():
    amend_bytes = AMEND.read_bytes()
    amend = json.loads(amend_bytes)
    floor = amend["coverage_floor"]
    assert floor == 0.80 and "including unavailable bars and session openings" in amend["minute_denominator"]
    res = {era: era_counts(era) for era in ("LEGACY", "RAW")}
    names = list(res["LEGACY"]["columns"])
    assert len(names) == 80 and names == list(res["RAW"]["columns"])

    # cross-check against the saved Step 3 full-run counts (same code, same TRAIN rows)
    mismatch = []
    for era in res:
        saved = json.loads((OUT / f"step3_{era}_report.json").read_text(encoding="utf-8"))["coverage_summary"]
        for key, v in saved.items():
            name = key.split(".", 1)[1]
            if name == EXCLUDED: continue
            if v["finite"] != res[era]["columns"][name]["finite"] or v["total"] != res[era]["rows"]: mismatch.append(f"{era}.{name}")
    assert not mismatch, f"counts differ from the saved Step 3 reports: {mismatch[:5]}"

    table = []
    for name in names:
        row = {"column": name}
        for era in res:
            r = res[era]
            row[f"{era}_finite"], row[f"{era}_rows"] = r["columns"][name]["finite"], r["rows"]
            row[f"{era}_pct"] = round(100 * r["columns"][name]["finite"] / r["rows"], 3)
        row["status"] = "PASS" if all(row[f"{e}_pct"] >= 100 * floor for e in res) else "BELOW"
        row["below_in"] = [e for e in res if row[f"{e}_pct"] < 100 * floor]
        table.append(row)

    ys = res["LEGACY"]["years"]
    by_year = pd.DataFrame({"column": names})
    for k, y in enumerate(ys):
        by_year[y] = [round(100 * res["LEGACY"]["columns"][n]["by_year"][k] / res["LEGACY"]["rows_by_year"][k], 3) for n in names]
    by_year.to_csv(OUT / "step6_coverage_LEGACY_by_year.csv", index=False)
    pd.DataFrame(table).drop(columns=["below_in"]).to_csv(OUT / "step6_coverage_TRAIN.csv", index=False)

    now = datetime.datetime.now(datetime.timezone.utc)
    report = dict(
        created_utc=now.isoformat(), descriptive_only=True,
        definition=dict(frozen_amendment=AMEND.name, frozen_amendment_sha256=sha(AMEND), amendment_id=amend["amendment_id"],
                        coverage_floor=floor, rounding="percent rounded to 3 decimals, compared with >= 100*floor (as in the Step 2 script)",
                        denominator=amend["minute_denominator"],
                        numerator="TRAIN rows where the column is finite (user decision; the amendment defines numerators only through family proxies)",
                        status_rule="PASS if BOTH eras are at least 80%, else BELOW",
                        note=amend["status"]),
        train_rows={e: res[e]["rows"] for e in res}, legacy_rows_by_year=dict(zip(ys, res["LEGACY"]["rows_by_year"])),
        excluded_from_detector=EXCLUDED, counts={k: sum(r["status"] == k for r in table) for k in ("PASS", "BELOW")},
        checked_against="saved Step 3 full-run counts: identical for all columns", columns=table)
    path = OUT / "step6_coverage_TRAIN.json"
    data = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    path.with_suffix(".sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    lines = ["| Column | LEGACY % | RAW % | Status |", "|---|---|---|---|"]
    for r in table:
        below = "" if r["status"] == "PASS" else " (" + ", ".join(r["below_in"]) + ")"
        lines.append(f"| {r['column']} | {r['LEGACY_pct']:.3f} | {r['RAW_pct']:.3f} | {r['status']}{below} |")
    (OUT / "step6_coverage_TRAIN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("\ncounts:", report["counts"], "| SHA-256:", digest)


if __name__ == "__main__":
    main()
