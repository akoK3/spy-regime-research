#!/usr/bin/env python3
"""Paper tables 3, 4, 5 and A3-A5 from stored result files. READ-ONLY on research results: it reads written JSON/CSV
outputs (and, for Table A3, hashes files that are present) and writes only paper/tables/.

Standard library only. Every value carries its source file and key in paper/tables/tables.json; the Markdown files are
the human-readable rendering. Tables A1 and A2 are text tables (amendment subjects, prespecified settings) with no
computed values and are not generated here.

One derived quantity, labelled in the output:
  Table 5, development H4 p-values use the A35 rule 1 convention (valid resamples only). The stored files keep the A29 1d
  convention (A35 1f): p_A29 = (1 + k) / (B + 1) with B = 9,999, so k = p_A29 * 10,000 - 1 and
  p_A35 = (1 + k) / (V + 1) with V = n_valid_resamples. This reproduces the AMENDMENT_A35.md table.

Usage: python paper/make_tables.py"""
import csv, hashlib, json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "paper" / "tables"
R5 = ROOT / "section5" / "results"
R6 = ROOT / "section6" / "results"
FAMS = [("gaussian_hmm", "Gaussian HMM"), ("student_t_hmm", "Student-t HMM"), ("hsmm", "HSMM"), ("bocpd", "BOCPD")]
ASSETS = [("TLT", "TLT"), ("HYG", "HYG"), ("GOLD", "gold"), ("DOLLAR", "dollar")]
VALUES = {}       # id -> {"value": ..., "source": "file#key"}


def L(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def rel(p):
    return str(Path(p).relative_to(ROOT)).replace("\\", "/")


def put(vid, value, src, key):
    VALUES[vid] = {"value": value, "source": f"{rel(src)}#{key}"}
    return value


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rnd(x, d):
    """Round half up (as in the paper), not Python's binary half-even: 794/800 = 99.25% -> 99.3."""
    return float(Decimal(repr(x)).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP))


def f(x, d=3, sign=False):
    x = rnd(x, d) + 0.0
    s = f"{x:+.{d}f}" if sign else f"{x:.{d}f}"
    return s.replace("-", "−")


def pfmt(p):
    return "1.0" if p == 1.0 else (f(p, 4) if p < 0.01 else f(p, 3))


# ---------------------------------------------------------------- Table 3: H1 development, uncontaminated folds
def table3():
    src = R5 / "main_run_2" / "run_summary.json"; s = L(src)
    a17 = R5 / "mr2" / "a17" / "a17_results.json"; h = L(a17)["h1c"]
    rows = ["| Family | H1(a) gain (share of folds > 0) | H1(b) gain (share of folds > 0) | p (IU) | Holm p | FOMC hit rate, feature / baseline |",
            "|---|---|---|---|---|---|"]
    for fam, name in FAMS:
        c = s["family_results"][fam]["confirmatory"]; k = f"family_results.{fam}.confirmatory"
        a = put(f"T3.{fam}.h1a_mean", c["H1a"]["mean"], src, k + ".H1a.mean")
        asc = put(f"T3.{fam}.h1a_sign", c["H1a"]["sign_consistency"], src, k + ".H1a.sign_consistency")
        b = put(f"T3.{fam}.h1b_mean", c["H1b"]["mean"], src, k + ".H1b.mean")
        bsc = put(f"T3.{fam}.h1b_sign", c["H1b"]["sign_consistency"], src, k + ".H1b.sign_consistency")
        piu = put(f"T3.{fam}.p_iu", c["p_iu"], src, k + ".p_iu")
        hp = s["holm"]["confirmatory"][fam]
        holm = "outside" if hp.get("secondary") else pfmt(put(f"T3.{fam}.holm_p", hp["p_adj"], src, f"holm.confirmatory.{fam}.p_adj"))
        fh = put(f"T3.{fam}.fomc_feature", h[fam]["f3"]["hit_rate"], a17, f"h1c.{fam}.f3.hit_rate")
        bh = put(f"T3.{fam}.fomc_baseline", h[fam]["base"]["hit_rate"], a17, f"h1c.{fam}.base.hit_rate")
        if fam == "bocpd":
            ga, gb = "0", "0"
        else:
            ga, gb = f"{f(a, 3, True)} ({f(asc, 2)})", f"{f(b, 3, True)} ({f(bsc, 2)})"
        rows.append(f"| {name} | {ga} | {gb} | {pfmt(piu)} | {holm} | {f(fh, 2)} / {f(bh, 2)} |")
    return "Table 3. H1 in development: uncontaminated folds.", rows


# ---------------------------------------------------------------- Table 4: H1 evaluation periods
def table4():
    rows = ["| Family | Era | H1(a) gain [95% CI] | H1(b) gain [95% CI] | QLIKE reduction | FOMC hit rate, feature / baseline |",
            "|---|---|---|---|---|---|"]
    for era in ("LEGACY", "RAW"):
        src = R5 / f"evaluation_{era}.json"; e = L(src)["families"]
        for fam, name in FAMS[:3]:
            g = e[fam]; k = f"families.{fam}"
            a = put(f"T4.{era}.{fam}.h1a", g["H1a"]["effect"], src, k + ".H1a.effect")
            alo, ahi = g["H1a"]["ci95"]; put(f"T4.{era}.{fam}.h1a_lo", alo, src, k + ".H1a.ci95[0]"); put(f"T4.{era}.{fam}.h1a_hi", ahi, src, k + ".H1a.ci95[1]")
            b = put(f"T4.{era}.{fam}.h1b", g["H1b"]["effect"], src, k + ".H1b.effect")
            blo, bhi = g["H1b"]["ci95"]; put(f"T4.{era}.{fam}.h1b_lo", blo, src, k + ".H1b.ci95[0]"); put(f"T4.{era}.{fam}.h1b_hi", bhi, src, k + ".H1b.ci95[1]")
            pct = put(f"T4.{era}.{fam}.qlike_pct", g["H1b"]["pct_of_baseline"], src, k + ".H1b.pct_of_baseline")
            fh = put(f"T4.{era}.{fam}.fomc_feature", g["H1c"]["feature"]["hit_rate"], src, k + ".H1c.feature.hit_rate")
            bh = put(f"T4.{era}.{fam}.fomc_baseline", g["H1c"]["baseline"]["hit_rate"], src, k + ".H1c.baseline.hit_rate")
            rows.append(f"| {name} | {era} | {f(a, 3, True)} [{f(alo)}, {f(ahi)}] | {f(b, 3, True)} [{f(blo)}, {f(bhi)}] | {f(pct, 1)}% | {f(fh, 2)} / {f(bh, 2)} |")
    return "Table 4. H1 on the evaluation periods (retrospective replication).", rows


# ---------------------------------------------------------------- Table 5: primary cross-asset tests
def a35_p(p_a29, v):
    k = round(p_a29 * 10000) - 1
    return (1 + k) / (v + 1)


def table5():
    cols = [("dev_gaussian_hmm", "development", "gaussian_hmm"), ("dev_hsmm", "development", "hsmm"), ("eval_gaussian_hmm", "evaluation", "gaussian_hmm")]
    ci_src = R6 / "posthoc" / "h3_ci_a29_3b.json"; ci = L(ci_src)["by_detector"]
    cells = {}
    for cid, period, det in cols:
        h2s = R6 / f"h2_{period}_{det}.json"; h2 = L(h2s)["primary"]
        s6s = R6 / f"s6_{period}_{det}.json"; s6 = L(s6s)["primary"]
        for a, an in ASSETS:
            t = h2[f"H2_{a}"]; p = put(f"T5.{cid}.H2_{a}.p", t["p"], h2s, f"primary.H2_{a}.p")
            n = t["n_breaks"]; put(f"T5.{cid}.H2_{a}.n", n, h2s, f"primary.H2_{a}.n_breaks")
            cells[(f"H2 {an}", cid)] = f"p {f(p, 3)}" + (f" ({n} breaks)" if n < 20 else "")
            t = s6[f"H3_{a}"]; g = put(f"T5.{cid}.H3_{a}.gamma", t["gamma"], s6s, f"primary.H3_{a}.gamma")
            p = put(f"T5.{cid}.H3_{a}.p", t["p"], s6s, f"primary.H3_{a}.p")
            txt = f(g)
            if period == "development" and a in ci.get(det, {}):
                lo, hi = ci[det][a]["ci95"]
                put(f"T5.{cid}.H3_{a}.ci_lo", lo, ci_src, f"by_detector.{det}.{a}.ci95[0]"); put(f"T5.{cid}.H3_{a}.ci_hi", hi, ci_src, f"by_detector.{det}.{a}.ci95[1]")
                txt += f" [{f(lo)}, {f(hi)}]"
            n = t["n_breaks"]
            cells[(f"H3 {an}", cid)] = f"{txt}; p {f(p, 3)}" + (f" ({n} breaks)" if n < 20 else "")
        for hk in ("H4a", "H4b"):
            t = s6[hk]; g = put(f"T5.{cid}.{hk}.gain", t["gain"], s6s, f"primary.{hk}.gain")
            if period == "development":
                p = a35_p(t["p"], t["n_valid_resamples"])
                VALUES[f"T5.{cid}.{hk}.p"] = {"value": p, "source": f"{rel(s6s)}#primary.{hk}.p,n_valid_resamples (A35 rule 1, derived)"}
            else:
                p = put(f"T5.{cid}.{hk}.p", t["p"], s6s, f"primary.{hk}.p")
            cells[(hk, cid)] = f"{f(g, 3, True)}; p {f(p, 3)}"
    order = [f"H2 {an}" for _, an in ASSETS] + [f"H3 {an}" for _, an in ASSETS] + ["H4a", "H4b"]
    rows = ["| Test | Development, Gaussian HMM | Development, HSMM | Evaluation, Gaussian HMM |", "|---|---|---|---|"]
    for r in order:
        rows.append(f"| {r} | " + " | ".join(cells[(r, c)] for c, _, _ in cols) + " |")
    return "Table 5. Primary cross-asset tests.", rows


# ---------------------------------------------------------------- Table A3: hashes of frozen records and input files
A3 = [  # label, expected SHA-256 (from REPRODUCIBILITY_FACTS.md §2-3), path relative to the repository root (None: not a file)
    ("Freeze document (evaluation token)", "846c1aaafaf1cb02911bc680c0b197f97e17b00386695fc0f6eb0b26b02e3a94", "section5/results/section5_freeze.json"),
    ("Freeze run record", "26d865e97d0da4ff4ad94362001522aa807d180447028cc73ccf04150837fae2", "section5/results/freeze_run_record.json"),
    ("Frozen-model manifest (8 models)", "edb78798544a8896c88f5a6b02857591d96f6764ed0d7f498685cbdbc0ac06dd", "section5/results/frozen_models/manifest.json"),
    ("Era-calibration lock", "db42bedef5c28b915e042a2494b60657d2be62948ba9453bd73b6daf2aad6e67", "section5/results/ERA_CALIBRATION.lock"),
    ("cross-asset fingerprint", "815c77623d6f14896becaef56356f2f55df5bfc9292281c4da6af876349e5de8", "section6/results/s6_fingerprint.json"),
    ("Detection protocol", "15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3", "SECTION5_PROTOCOL.md"),
    ("Contamination registry", "f6d67a57ca30184bc6f2f00f5a4e3aafa0d8808a6e90784def110cdaf19d067b", "freeze:contamination_sha256"),
    ("Completion record", "19812f9f619f029b949bdc9e123c78007a4e71bf668f214569a5bbe12577079a", "section5/results/main_run_2/run_complete.json"),
    ("Evaluation FOMC schedule", "391366459f83a89e2442f05479774b49f8efac1479a92daf9ceda0e0d36b6865", "section5/results/h1c_schedule_times_evaluation.json"),
    ("Canonical panel, LEGACY", "b5967d9691c547a3b8a277f97fe2a95e1b1c4a49e4d6476c008a08076ce098df", "section3_10_alignment_results/canonical_panel_LEGACY_1m.csv.gz"),
    ("Canonical panel, RAW", "f1b1c498dc76c7ef11e53a31fec655abacaf6458d8f3b9dd1827f9dd8ec91184", "section3_10_alignment_results/canonical_panel_RAW_1m.csv.gz"),
    ("SPY file, LEGACY", "7cd10dfb3e5896b9574a53f35914ce43053705cff9c5ef7029ccb2b88a6c83f7", "section3_4_etf_results/etf_observed_SPY_LEGACY.csv.gz"),
    ("SPY file, RAW", "6c37b2798d3cc5740d71de94c34343d315fa274b95e50a5a7df081c1b7a5928d", "section3_4_etf_results/etf_observed_SPY_RAW.csv.gz"),
    ("Feature-construction frozen matrix", "9378f93f79e358f98d9dcad3992c269cb9a823a15bf28e8a21dbe319763ebe86", "section431_step3_all_in_one_results/a4_sec4_3_9_frozen_matrix_v2.csv"),
    ("Feature-construction development folds", "06258e5a1645327a64aa07d155b59d20949c11c81ce657a26e4d44c27882adfc", "section431_step3_all_in_one_results/a4_development_nested_folds_TRAIN.csv"),
]


def table_a3():
    fz_src = R5 / "section5_freeze.json"; fz = L(fz_src)
    rows = ["| Record or file | SHA-256 | Path | Status |", "|---|---|---|---|"]
    cv = put("A3.code_version", fz["code_version"], fz_src, "code_version")
    rows.append(f"| Code version (16 characters) | {cv} | `section5_freeze.json#code_version` | recorded |")
    for label, exp, path in A3:
        vid = "A3." + label.split(" (")[0].lower().replace(" ", "_").replace(",", "").replace("-", "_")
        if path.startswith("freeze:"):
            key = path.split(":", 1)[1]; got = fz[key]; status = "OK (freeze key)" if got == exp else "MISMATCH"
            VALUES[vid] = {"value": got, "source": f"{rel(fz_src)}#{key}"}; shown = f"`section5_freeze.json#{key}`"
        else:
            p = ROOT / path; shown = f"`{path}`"
            if p.exists():
                got = sha(p); status = "OK" if got == exp else "MISMATCH"
                VALUES[vid] = {"value": got, "source": f"sha256({path})"}
            else:
                status = "not present (data or git-ignored file)"
        rows.append(f"| {label} | {exp} | {shown} | {status} |")
    return "Table A3. Hashes of the frozen records and input files.", rows


# ---------------------------------------------------------------- Table A4: cross-asset coverage
def table_a4():
    summ_src = R6 / "coverage" / "coverage_summary.json"; summ = L(summ_src)
    ev_src = R6 / "coverage_evaluation.json"; ev = L(ev_src)
    dev = {}
    with open(R6 / "coverage" / "coverage_sessions.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            d = dev.setdefault((r["era"], r["asset"]), [0, 0]); d[1] += 1; d[0] += r["available"] == "True"
    evc = {}
    for r in ev["rows"]:
        d = evc.setdefault((r["era"], r["asset"]), [0, 0]); d[1] += 1; d[0] += bool(r["available"])
    rows = ["| Asset | LEGACY development | RAW development | LEGACY evaluation | RAW evaluation |", "|---|---|---|---|---|"]
    for a, an in ASSETS:
        cells = []
        for era, tab, src in (("LEGACY", dev, "section6/results/coverage/coverage_sessions.csv"), ("RAW", dev, "section6/results/coverage/coverage_sessions.csv"),
                              ("LEGACY", evc, rel(ev_src)), ("RAW", evc, rel(ev_src))):
            k, n = tab[(era, a)]; per = "development" if tab is dev else "evaluation"
            VALUES[f"A4.{a}.{era}.{per}.n"] = {"value": k, "source": f"{src}#available (era={era}, asset={a})"}
            VALUES[f"A4.{a}.{era}.{per}.share"] = {"value": 100 * k / n, "source": f"{src}#available share"}
            cells.append(f"{k:,} ({f(100 * k / n, 1)}%)")
        rows.append(f"| {'Dollar index' if a == 'DOLLAR' else an.capitalize() if a == 'GOLD' else an} | " + " | ".join(cells) + " |")
    VALUES["A4.rule"] = {"value": summ.get("rule"), "source": f"{rel(summ_src)}#rule"}
    return "Table A4. Sessions available for each cross-asset market (share of the period's sessions).", rows


# ---------------------------------------------------------------- Table A5: primary feature pool
def table_a5():
    src = ROOT / "section431_step3_all_in_one_results" / "a4_sec4_3_9_frozen_matrix_v2.csv"
    with open(src, newline="", encoding="utf-8") as fh:
        rows_in = list(csv.DictReader(fh))
    rows = ["| Column | Coverage LEGACY / RAW (%) |", "|---|---|"]
    # 19 columns are "kept" after the coverage and redundancy rules. AMENDMENT_A20 rule 1: scale-type = name stems rv,
    # downside, abs_return, intrabar_range; drop each raw scale column whose __sadj version is in the pool -> 13 columns.
    kept = {r["column"] for r in rows_in if r["primary_outcome"] == "kept"}
    scale = ("rv", "downside", "abs_return", "intrabar_range")
    for r in rows_in:
        c = r["column"]
        if c in kept and not (c.startswith(scale) and not c.endswith("__sadj") and f"{c}__sadj" in kept):
            lo = put(f"A5.{c}.cov_legacy", float(r["coverage_LEGACY_pct"]), src, f"{c}.coverage_LEGACY_pct")
            hi = put(f"A5.{c}.cov_raw", float(r["coverage_RAW_pct"]), src, f"{c}.coverage_RAW_pct")
            rows.append(f"| {c} | {f(lo, 1)} / {f(hi, 1)} |")
    return "Table A5. Primary feature pool: coverage of TRAIN minutes (from the frozen matrix v2).", rows


# ---------------------------------------------------------------- Benchmark numbers quoted in the paper's text (§6.2)
def benchmark():
    """Post hoc benchmark (development, confirmatory folds). Each value comes from posthoc_benchmark.json; the number
    printed in BENCHMARK_FACTS.md for the same quantity is stored as "facts" so the checker can compare both."""
    import re
    BD = R5 / "posthoc_benchmark"; src = BD / "posthoc_benchmark.json"; b = L(src); ab = b["absolute"]["confirmatory"]
    facts_md = (BD / "BENCHMARK_FACTS.md").read_text(encoding="utf-8")
    a17 = R5 / "mr2" / "a17" / "a17_results.json"; h1c = L(a17)["h1c"]

    def fact(pattern, group=1):
        m = re.search(pattern, facts_md, re.M)
        return m.group(group) if m else None

    def putf(vid, value, s, key, facts):
        put(vid, value, s, key); VALUES[vid]["facts"] = facts; VALUES[vid]["facts_source"] = rel(BD / "BENCHMARK_FACTS.md")
        return value

    rows = ["| Quantity | Value | BENCHMARK_FACTS.md |", "|---|---|---|"]
    v = putf("BM.pauc.B1", ab["B1"]["pauc_mean"], src, "absolute.confirmatory.B1.pauc_mean", fact(r"^\| B1 \| ([0-9.]+) \|$"))
    rows.append(f"| pAUC, volatility-change rule B1 | {f(v)} | {VALUES['BM.pauc.B1']['facts']} |")
    names = {"gaussian_hmm": "Gaussian HMM", "student_t_hmm": "Student-t HMM", "hsmm": "HSMM"}
    for fam, nm in names.items():
        v = putf(f"BM.pauc.{fam}", ab[fam]["pauc_feature_mean"], src, f"absolute.confirmatory.{fam}.pauc_feature_mean",
                 fact(rf"^\| {re.escape(nm)}, feature / baseline \| ([0-9.]+) /"))
        rows.append(f"| pAUC, {nm} feature model | {f(v)} | {VALUES[f'BM.pauc.{fam}']['facts']} |")
    v = putf("BM.fomc.B1_pct", 100 * b["fomc"]["B1"]["hit_rate"], src, "fomc.B1.hit_rate (x100)", fact(r"^\| B1 \| ([0-9.]+) \("))
    VALUES["BM.fomc.B1_pct"]["facts_scale"] = 100
    rows.append(f"| FOMC hit rate, B1 (%) | {f(v, 1)} | {VALUES['BM.fomc.B1_pct']['facts']} |")
    for fam in ("gaussian_hmm", "hsmm"):
        v = putf(f"BM.fomc.{fam}_pct", 100 * h1c[fam]["f3"]["hit_rate"], a17, f"h1c.{fam}.f3.hit_rate (x100)",
                 fact(rf"^\| {re.escape(names[fam])} \| ([0-9.]+) \| \d+ / \d+ /"))
        VALUES[f"BM.fomc.{fam}_pct"]["facts_scale"] = 100
        rows.append(f"| FOMC hit rate, {names[fam]} (%) | {f(v, 1)} | {VALUES[f'BM.fomc.{fam}_pct']['facts']} |")
    v = putf("BM.qlike.HAR_same_bars", ab["gaussian_hmm"]["qlike_HAR_same_bars_fold_mean"], src,
             "absolute.confirmatory.gaussian_hmm.qlike_HAR_same_bars_fold_mean", fact(r"^\| Gaussian HMM \| [0-9.]+ \| ([0-9.]+) \|"))
    rows.append(f"| QLIKE, HAR on the Gaussian HMM's bars | {f(v, 4)} | {VALUES['BM.qlike.HAR_same_bars']['facts']} |")
    det = {fam: ab[fam]["qlike_detector_fold_mean"] for fam in names}
    dfacts = {fam: fact(rf"^\| {re.escape(nm)} \| ([0-9.]+) \| [0-9.]+ \|") for fam, nm in names.items()}
    lo, hi = min(det, key=det.get), max(det, key=det.get)
    putf("BM.qlike.detector_min", det[lo], src, f"absolute.confirmatory.{lo}.qlike_detector_fold_mean (min over G, T, H)", dfacts[lo])
    putf("BM.qlike.detector_max", det[hi], src, f"absolute.confirmatory.{hi}.qlike_detector_fold_mean (max over G, T, H)", dfacts[hi])
    rows.append(f"| QLIKE, feature detectors (range over G, T, H) | {f(det[lo], 4)} to {f(det[hi], 4)} | {dfacts[lo]} to {dfacts[hi]} |")
    units = [L(p) for p in sorted((BD / "units").glob("*.json"))]; conf = [u for u in units if u["confirmatory"]]
    put("BM.n_confirmatory_folds", len(conf), BD / "units", "count(units/*.json with confirmatory = true)")
    for fam, nm in names.items():
        k = sum(1 for u in conf if u["families"][fam]["h1b_vs_HAR"]["effect"] < 0)
        share = b["comparison"][fam]["h1b_vs_HAR"]["confirmatory"]["sign_consistency"]
        put(f"BM.har_better_folds.{fam}", k, BD / "units", f"count(units/*.json confirmatory, families.{fam}.h1b_vs_HAR.effect < 0)")
        # BENCHMARK_FACTS.md §3 prints the share of folds where the detector is better; HAR-better = n - share * n.
        sec3 = facts_md[facts_md.index("## 3. Forecasting"):facts_md.index("## 4.")]
        m = re.search(rf"^\| {re.escape(nm)} \| [−-][0-9.]+ / [0-9.]+ / ([0-9.]+) \|", sec3, re.M)
        VALUES[f"BM.har_better_folds.{fam}"]["facts"] = m.group(1) if m else None
        VALUES[f"BM.har_better_folds.{fam}"]["facts_kind"] = "detector_better_share"
        VALUES[f"BM.har_better_folds.{fam}"]["facts_source"] = rel(BD / "BENCHMARK_FACTS.md")
        VALUES[f"BM.har_better_folds.{fam}"]["detector_better_share"] = share
        rows.append(f"| Folds where HAR beats {nm} on QLIKE | {k} of {len(conf)} | detector better in share {VALUES[f'BM.har_better_folds.{fam}']['facts']} |")
    return "Benchmark numbers quoted in §6.2 (post hoc; development, confirmatory folds).", rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    md = ["# Paper tables (generated)", "", "Generated by `paper/make_tables.py` from stored result files; do not edit by hand.",
          "Every value and its source key are in `tables.json`. Tables A1 and A2 are text tables and are not generated.", ""]
    for fn in (table3, table4, table5, table_a3, table_a4, table_a5, benchmark):
        title, rows = fn(); md += [f"## {title}", ""] + rows + [""]
    (OUT / "TABLES.md").write_text("\n".join(md), encoding="utf-8")
    (OUT / "tables.json").write_text(json.dumps(VALUES, indent=1, sort_keys=True, default=str), encoding="utf-8")
    print(f"wrote {rel(OUT / 'TABLES.md')} and tables.json ({len(VALUES)} values)")


if __name__ == "__main__":
    main()
