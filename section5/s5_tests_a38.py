#!/usr/bin/env python3
"""Tests for s5_a38 (AMENDMENT_A38 rule 1 entry; PREFREEZE_AUDIT M4). Synthetic data only; no HF file, panel or evaluation row is read."""
import sys, json, tempfile, unittest
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "section6"))
import s5_a38 as A, s5_eval_loader as EL, s5_eval_label as EV

MIN = 60_000_000_000


def grid(days=("2024-07-01", "2024-07-02"), n=390):
    t, day, slot, first, end = [], [], [], [], []
    for d in days:
        s = pd.Timestamp(d + " 09:30", tz="America/New_York").tz_convert("UTC").value; first.append(len(t))
        t += [s + k * MIN for k in range(n)]; day += [d] * n; slot += list(range(n)); end.append(len(t))
    return dict(t=np.array(t, np.int64), day=np.array(day), slot=np.array(slot), first=np.array(first), end=np.array(end))


def hf_rows(days=("2024-07-01", "2024-07-02"), n=390, drop=(), bad=(), extra_off_grid=True):
    rows = []
    for d in days:
        for k in range(n):
            if (d, k) in drop: continue
            ts = (pd.Timestamp(d + " 09:30") + pd.Timedelta(minutes=k)).strftime("%Y-%m-%d %H:%M:%S"); c = 500 + 0.01 * k
            rows.append(dict(datetime=ts, Open=c, High=(c - 1 if (d, k) in bad else c + 0.02), Low=c - 0.02, Close=c, Volume=100, source="iex"))
        if extra_off_grid: rows.append(dict(datetime=d + " 16:00:00", Open=1, High=1, Low=1, Close=1, Volume=1, source="iex"))
    return pd.DataFrame(rows)


class TestPanel(unittest.TestCase):
    def test_grid_mapping_eligibility_and_validity(self):
        g = grid(); d, cnt = A.build_panel("RAW", g, hf_rows(drop={("2024-07-01", 10)}, bad={("2024-07-02", 5)}))
        self.assertEqual(cnt["off_grid"], 2); self.assertEqual(cnt["invalid_ohlcv"], 1); self.assertEqual(cnt["observed_minutes"], 2 * 390 - 2)
        i10 = 10; i5 = 390 + 5
        self.assertTrue(np.isnan(d["close"][i10])); self.assertFalse(d["valid"][i10]); self.assertFalse(d["valid"][i10 + 1])      # missing bar: no return into it or out of it
        self.assertFalse(d["valid"][0]); self.assertFalse(d["valid"][390])                                                           # session opens: never eligible
        self.assertTrue(np.isnan(d["close"][i5])); self.assertTrue(d["valid"][12]); self.assertAlmostEqual(d["r"][12], np.log(d["close"][12] / d["close"][11]))
        self.assertTrue(np.array_equal(np.isfinite(d["r"]), d["valid"])); self.assertTrue(np.all(d["available"] == d["t"] + MIN))

    def test_read_hf_refuses_other_sources(self):
        with tempfile.TemporaryDirectory() as td:
            import zipfile
            p = Path(td) / "x.zip"; df = hf_rows(days=("2024-07-01",), n=5, extra_off_grid=False); df.loc[2, "source"] = "pitrading"
            with zipfile.ZipFile(p, "w") as z: z.writestr("SPY_raw_1min.csv", df.to_csv(index=False))
            with self.assertRaises(PermissionError): A.read_hf(p, "SPY_raw_1min.csv", "2024-07-01", "2024-07-01")
            self.assertEqual(len(A.read_hf(p, "SPY_raw_1min.csv", "2024-07-02", "2024-07-03")), 0)      # rows outside the span are never kept


class TestStatistics(unittest.TestCase):
    def test_boot_mean_diff_and_mde(self):
        rng = np.random.default_rng(1); cl = np.repeat(np.arange(60), 20); y0 = rng.normal(0, 1, len(cl)); same = A.boot_mean_diff(y0, y0, cl, 300)
        self.assertEqual(same["effect"], 0.0); self.assertAlmostEqual(same["sd"], 0.0); shift = A.boot_mean_diff(y0 + 1.0, y0, cl, 300)
        self.assertAlmostEqual(shift["effect"], 1.0); self.assertGreater(shift["ci95"][0], 0.9); noisy = A.boot_mean_diff(y0 + rng.normal(0, 1, len(cl)), y0, cl, 300)
        self.assertAlmostEqual(noisy["mde"], A.Z * noisy["sd"]); self.assertLess(noisy["ci95"][0], noisy["ci95"][1])

    def runs(self, shift_clean=0.0):
        rng = np.random.default_rng(2); keys = np.array([s * 1000 + b for s in range(40) for b in range(20)])
        def fam(loss_shift):
            lb = rng.gamma(2, 1, len(keys)); lf = lb - 0.1 + loss_shift
            return dict(lb=lb, kb=keys, lf=lf, kf=keys, h1a_note="synthetic: no splices")
        return dict(families={"gaussian_hmm": fam(0.0)}), dict(families={"gaussian_hmm": fam(shift_clean)})

    def test_compare_identical_runs_and_detects_a_filter_effect(self):
        raw, _ = self.runs(); r = A.compare(raw, raw, 300)["gaussian_hmm"]
        self.assertEqual(r["H1b"]["delta"]["effect"], 0.0); self.assertIsNone(r["H1a"]["delta"]); self.assertEqual(r["reading"], "not evaluable on both components")
        raw, clean = self.runs(shift_clean=0.5); r = A.compare(raw, clean, 300)["gaussian_hmm"]
        self.assertLess(r["H1b"]["delta"]["ci95"][1], 0); self.assertEqual(r["H1b"]["n_common_bars"], 800)

    def test_secondary_labels(self):
        off = dict(families={f: dict(H1a=dict(effect=e, ci95=[e - 0.05, e + 0.05]), H1b=dict(effect=0.02, ci95=[0.01, 0.03])) for f, e in (("gaussian_hmm", 0.1), ("hsmm", 0.03), ("student_t_hmm", 0.2), ("bocpd", 0.0))})
        fz = dict(h1_verdicts={"gaussian_hmm": dict(reject=True), "hsmm": dict(reject=True), "student_t_hmm": dict(reject=False), "bocpd": dict(reject=False, secondary=True)})
        s = A.secondary(off, fz)
        self.assertEqual(s["gaussian_hmm"]["label"], "robust to the LEGACY Clean filter"); self.assertTrue(s["hsmm"]["label"].startswith("possibly filter-dependent"))
        self.assertIsNone(s["student_t_hmm"]["label"]); self.assertIsNone(s["bocpd"]["label"]); self.assertAlmostEqual(s["gaussian_hmm"]["H1a"]["mde_approx"], A.Z * 0.1 / 3.92)


class TestGuards(unittest.TestCase):
    def test_authorise_a38_refusals_are_logged(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); saved = (EL.ACCESS_LOG, EL._checks, EL.A38_RESULTS)
            try:
                EL.ACCESS_LOG = td / "log.txt"; EL._checks = lambda *a, **k: {}; EL.A38_RESULTS = td
                with self.assertRaises(PermissionError): EL.authorise_a38("raw", td / "fz.json", "t")          # no official 5.13 RAW result yet
                with self.assertRaises(PermissionError): EL.authorise_a38("other", td / "fz.json", "t")
                (td / "evaluation_RAW.json").write_text(json.dumps(dict(x=1)))
                with self.assertRaises(PermissionError): EL.authorise_a38("raw", td / "fz.json", "t")          # unlabelled official result
                (td / "evaluation_RAW.json").write_text(json.dumps(dict(x=1, a26_label=EV.LABEL, confirmatory=False))); n0 = len(EL.EVAL_READS)
                self.assertEqual(EL.authorise_a38("raw", td / "fz.json", "t"), EL.EVAL["RAW"]); self.assertEqual(EL.EVAL_READS[-1], ("RAW", "a38:raw"))
                log = EL.ACCESS_LOG.read_text(); self.assertEqual(log.count("REFUSED A38"), 3); self.assertEqual(log.count("ALLOWED A38"), 1)
            finally: EL.ACCESS_LOG, EL._checks, EL.A38_RESULTS = saved; del EL.EVAL_READS[n0:]

    def test_run_file_checks_hash_then_marker(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); f = td / "hf.zip"; f.write_bytes(b"x"); saved = (dict(A.HF), EL.authorise_a38)
            try:
                A.HF["raw"] = dict(file=f, member="SPY_raw_1min.csv", sha256="0" * 64)
                with self.assertRaises(PermissionError): A.run_file("raw", td / "fz.json", "t", {}, res=td)          # file differs from the recorded hash
                A.HF["raw"] = dict(file=f, member="SPY_raw_1min.csv", sha256=A.sha(f)); EL.authorise_a38 = lambda *a, **k: EL.EVAL["RAW"]; A.marker("raw", td).write_text("x")
                with self.assertRaises(SystemExit): A.run_file("raw", td / "fz.json", "t", {}, res=td)               # one-shot marker exists: no second read
            finally: A.HF.clear(); A.HF.update(saved[0]); EL.authorise_a38 = saved[1]

    def test_registered_and_fingerprinted(self):
        import s5_contamination as CT, s6_fingerprint as FPM
        self.assertEqual(CT.REGISTRY.get("s5_a38.py"), "EVALUATION"); self.assertIn("s5_a38.py", FPM.HELPERS); self.assertTrue(CT.DATA_LOAD.search("hfdatalibrary_raw"))


if __name__ == "__main__": unittest.main()
