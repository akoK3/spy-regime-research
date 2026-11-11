#!/usr/bin/env python3
"""Freeze-prep tests: amendment manifest (A26 2b/2c, A27 3d), guarded evaluation loader, break export loops (confirmed runs equal the detectors; fizzles recorded)."""
import sys, json, gzip, hashlib, tempfile, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import s5_amendment_manifest as AM, s5_eval_loader as EL, s5_break_export as BX, s5_events as E, s5_freeze as FZ

M = 60 * 10 ** 9


def fake_amendment(root, name, status="ADOPTED", sidecar=True, tamper=False):
    p = root / f"AMENDMENT_{name}.md"; p.write_text(f"# Amendment {name}\n\nDated x. Status: {status} 2026-11-09.\n", encoding="utf-8")
    if sidecar: (root / f"AMENDMENT_{name}.sha256").write_text(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n", encoding="ascii")
    if tamper: p.write_text(p.read_text(encoding="utf-8") + "x", encoding="utf-8")


class TestManifest(unittest.TestCase):
    def test_ready_and_refusals(self):
        with tempfile.TemporaryDirectory() as td:
            r = Path(td); done = r / "done.json"; done.write_text("{}")
            for n in ("X1", "X2"): fake_amendment(r, n)
            man = AM.freeze_ready(("X1", "X2"), r, {"A27": done}); self.assertEqual([e["status"] for e in man], ["ADOPTED", "ADOPTED"]); self.assertTrue(all(e["sidecar_matches"] for e in man))
            with self.assertRaisesRegex(PermissionError, "A27 result"): AM.freeze_ready(("X1",), r, {"A27": r / "missing.json"})
            fake_amendment(r, "X3", status="DRAFT")
            with self.assertRaisesRegex(PermissionError, "DRAFT"): AM.freeze_ready(("X1", "X3"), r, {})
            fake_amendment(r, "X4", tamper=True)
            with self.assertRaisesRegex(PermissionError, "differs from its sidecar"): AM.freeze_ready(("X4",), r, {})
            fake_amendment(r, "X5", sidecar=False)
            with self.assertRaisesRegex(PermissionError, "no sidecar"): AM.freeze_ready(("X5",), r, {})
            with self.assertRaisesRegex(PermissionError, "missing"): AM.freeze_ready(("X9",), r, {})

    def test_repository_amendments(self):
        man = AM.manifest()
        self.assertEqual([e["amendment"] for e in man], list(AM.AMENDMENTS))
        for e in man:
            if e["present"] and e["status"] == "ADOPTED": self.assertTrue(e["sidecar_matches"], e)      # adopted: sidecar equal
        self.assertTrue({"A29", "A30", "A31", "A32", "A33", "A33_1", "A34", "A35", "A36", "A37", "A38"} <= set(AM.AMENDMENTS))          # FABLE_AUDIT L5; A30, A32, A33, A33.1, A34 added when written
        if not all(e["present"] and e["status"] == "ADOPTED" and e["sidecar_matches"] for e in man):
            with self.assertRaises(PermissionError): AM.freeze_ready()                                       # a DRAFT or missing amendment blocks the freeze

    def test_freeze_carries_list(self):
        man = [dict(amendment="X1", sha256="ab")]; doc = FZ.build_freeze({}, {}, {}, {}, {}, "ph", man); self.assertEqual(doc["amendments"], man)


def fake_panel(p, days):
    rows = ["utc_minute_start_assumed,available_utc_assuming_minute_start,session_date_ny,minute_index_in_session,SPY_log_return_1m"]
    for d in days:
        for m in range(3): rows.append(f"{d}T14:3{m}:00Z,{d}T14:3{m + 1}:00Z,{d},{m},{0.001 * m}")
    with gzip.open(p, "wt", encoding="utf-8") as f: f.write("\n".join(rows) + "\n")


class TestEvalLoader(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory(); self.r = Path(self.td.name); EL.ACCESS_LOG = self.r / "access.txt"; self.panel = self.r / "p.csv.gz"
        fake_panel(self.panel, ["2018-12-20", "2018-12-21", "2018-12-24", "2019-01-02", "2022-03-04", "2022-03-07"])
        self.done = self.r / "done.json"; self.done.write_text("{}"); fake_amendment(self.r, "X1"); self.man = AM.freeze_ready(("X1",), self.r, {"A27": self.done})
        self.fz = FZ.write_freeze(FZ.build_freeze({}, {}, {}, {}, {}, "ph", self.man), self.r); self.tok = EL.sha(self.fz); self.lock = self.r / "lock"; self.lock.write_text("x")
        self._fr = AM.freeze_ready; AM.freeze_ready = lambda: self.man
        self._saved = (EL.PANELS, EL.LOCK, EL._preflight, EL.FINGERPRINT); EL.PANELS = {"LEGACY": self.panel, "RAW": self.panel}; EL.LOCK = self.lock; EL._preflight = lambda: 0
        import s5_eval_label as EV; self.EV = EV; EV.ACTIVE = True; self._reads = list(EL.EVAL_READS)      # FABLE_REAUDIT M3: a Section 5 evaluation read needs the labelled 5.13 entry to be active

    def tearDown(self): AM.freeze_ready = self._fr; EL.PANELS, EL.LOCK, EL._preflight, EL.FINGERPRINT = self._saved; self.EV.ACTIVE = False; EL.EVAL_READS[:] = self._reads; self.td.cleanup()

    def test_dev_spans(self): self.assertTrue(EL.check_dev_spans())

    def test_development_only(self):
        df = EL.load_development("LEGACY", ["SPY_log_return_1m"], panel=self.panel); self.assertEqual(sorted(set(df["session_date_ny"])), ["2018-12-20", "2018-12-21"])

    def test_eval_allowed(self):
        df = EL.load_eval("LEGACY", ["SPY_log_return_1m"], self.fz, self.tok)
        self.assertEqual(sorted(set(df["session_date_ny"])), ["2019-01-02", "2022-03-04"]); self.assertIn("ALLOWED", EL.ACCESS_LOG.read_text())
        self.assertEqual(EL.EVAL_READS[-1], ("LEGACY", False))                                              # the read is recorded for the Section 6 write guard

    def test_eval_refused_outside_labelled_entry(self):
        self.EV.ACTIVE = False
        with self.assertRaisesRegex(PermissionError, "run_confirmatory_labelled"): EL.load_eval("LEGACY", ["SPY_log_return_1m"], self.fz, self.tok)
        self.assertIn("REFUSED", EL.ACCESS_LOG.read_text()); self.assertEqual(EL.EVAL_READS, self._reads)

    def test_eval_refusals(self):
        kw = {}
        with self.assertRaisesRegex(PermissionError, "confirm_token"): EL.load_eval("LEGACY", [], self.fz, "0" * 64)
        EL.LOCK = self.r / "nolock"
        with self.assertRaisesRegex(PermissionError, "lock"): EL.load_eval("LEGACY", [], self.fz, self.tok)
        EL.LOCK = self.lock; EL._preflight = lambda: 1
        with self.assertRaisesRegex(PermissionError, "preflight"): EL.load_eval("LEGACY", [], self.fz, self.tok)
        EL._preflight = lambda: 0; EL.FINGERPRINT = self.r / "nofp.json"
        with self.assertRaisesRegex(PermissionError, "fingerprint"): EL.load_eval("LEGACY", [], self.fz, self.tok, section6=True)
        AM.freeze_ready = lambda: self.man + [dict(amendment="X2")]
        with self.assertRaisesRegex(PermissionError, "amendment list"): EL.load_eval("LEGACY", [], self.fz, self.tok, **kw)
        self.fz.write_text(self.fz.read_text() + " ")
        with self.assertRaises(RuntimeError): EL.load_eval("LEGACY", [], self.fz, self.tok, **kw)
        self.assertEqual(EL.ACCESS_LOG.read_text().count("REFUSED"), 6)

    def test_no_override_arguments(self):
        import inspect
        self.assertEqual(list(inspect.signature(EL.load_eval).parameters), ["era", "columns", "freeze_path", "confirm_token", "section6"])
        self.assertEqual(list(inspect.signature(EL.eval_guard).parameters), ["era", "freeze_path", "confirm_token", "section6"])
        with self.assertRaises(TypeError): EL.load_eval("LEGACY", [], self.fz, self.tok, preflight=lambda: 0)


class TestBreakLoops(unittest.TestCase):
    def test_old_state_runs(self):
        rng = np.random.default_rng(5)
        for _ in range(40):
            T = 78; P = rng.dirichlet(np.full(3, 0.3), T); real = rng.random(T) > 0.05; av = ((np.arange(T) * 5 + 1) * M).astype(np.int64)
            for th in (0.0, 1.0, 3.0):
                runs = BX.runs_old_state(P, real, av, th); ref = E.detect_old_state_logodds(P, real, av, th)[0]
                self.assertEqual([(x["i_d"], x["i_end"]) for x in runs if x["kind"] == "confirmed"], [(e["i_d"], e["i_c"]) for e in ref])
                self.assertEqual(sum(x["kind"] == "open_at_close" for x in runs), E.detect_old_state_logodds(P, real, av, th)[1])
                for x in runs:
                    if x["kind"] == "fizzle": self.assertLess(x["i_end"] - x["i_d"], 3)

    def test_fizzle_recorded(self):
        P = np.tile([0.99, 0.01], (30, 1)); P[10:12] = [0.01, 0.99]; real = np.ones(30, bool); av = ((np.arange(30) * 5 + 1) * M).astype(np.int64)
        runs = BX.runs_old_state(P, real, av, 0.0); self.assertEqual([(x["kind"], x["i_d"], x["i_end"]) for x in runs], [("fizzle", 10, 11)])

    def test_bocpd_runs(self):
        rng = np.random.default_rng(6)
        for _ in range(40):
            T = 78; R = np.maximum(0, np.cumsum(rng.integers(-6, 3, size=T)) + 40).astype(float); real = rng.random(T) > 0.05; av = ((np.arange(T) * 5 + 1) * M).astype(np.int64)
            for m in (1.0, 3.0, 6.0):
                runs = BX.runs_bocpd(R, real, av, m); ref = E.detect_bocpd_map(R, real, av, m)[0]
                self.assertEqual([(x["i_d"], x["i_end"]) for x in runs if x["kind"] == "confirmed"], [(e["i_d"], e["i_c"]) for e in ref])
                self.assertEqual(sum(x["kind"] == "open_at_close" for x in runs), E.detect_bocpd_map(R, real, av, m)[1])

    def test_direction_and_size(self):
        class Mod: var = np.array([[1.0, 1.0], [4.0, 1.0]])
        P = np.tile([0.99, 0.01], (30, 1)); P[10:] = [0.01, 0.99]; real = np.ones(30, bool); av = ((np.arange(30) * 5 + 1) * M).astype(np.int64)
        q = dict(n=30, real=real, avail=av, slots=np.arange(30) * 5 + 4)
        rows = BX.session_rows("gaussian_hmm", Mod(), dict(P=P), q, 0.0, "2010-01-04", dict(fold="LEGACY|0", era="LEGACY", K=2))
        self.assertEqual(len(rows), 1); x = rows[0]; self.assertEqual(x["direction"], "calm_to_stressed"); self.assertAlmostEqual(x["size"], np.log(4.0))
        self.assertEqual((x["S_min"], x["T0_min"]), (55, 65)); self.assertEqual(x["prior_calm_min"], 50.0)


if __name__ == "__main__": unittest.main()
