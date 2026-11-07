#!/usr/bin/env python3
"""Ledger integrity tests (standalone, standard library only; no data, no models).

1. The live METHODS_LEDGER.md matches METHODS_LEDGER.sha256: SHA-256 of the ledger's exact bytes (CRLF and LF
   are hashed as they are on disk) against the first token of the sidecar (the sidecar's own line ending is ignored).
2. s5_ledger.add on the live ledger path rewrites the sidecar (checked on a temporary copy).

Background: rows appended to the ledger without `s5_ledger.py add` left the sidecar stale (2026-11-07). From then on
every ledger row goes through `s5_ledger.py add`; run this file after adding rows:
  python section5/s5_tests_ledger.py"""
import sys, hashlib, shutil, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import s5_ledger as LED


def _sidecar_hash(side):
    tok = Path(side).read_bytes().decode("ascii").split()
    if len(tok) < 2: raise AssertionError(f"{side} is not '<sha256>  <file name>'")
    return tok[0], tok[1]


class TestLedgerSidecar(unittest.TestCase):
    def test_live_ledger_matches_sidecar(self):
        led, side = ROOT / "METHODS_LEDGER.md", ROOT / "METHODS_LEDGER.sha256"
        self.assertTrue(led.exists() and side.exists(), "ledger or sidecar missing")
        h, name = _sidecar_hash(side)
        self.assertEqual(name, "METHODS_LEDGER.md")
        actual = hashlib.sha256(led.read_bytes()).hexdigest()
        self.assertEqual(h, actual, f"METHODS_LEDGER.sha256 says {h[:16]}..., ledger bytes hash to {actual[:16]}...; "
                                    "a row was probably added without s5_ledger.py add")

    def test_add_rewrites_sidecar(self):
        old = (LED.LEDGER, LED.SIDE)
        with tempfile.TemporaryDirectory() as td:
            led = Path(td) / "METHODS_LEDGER.md"; side = led.with_suffix(".sha256")
            shutil.copyfile(ROOT / "METHODS_LEDGER.md", led); side.write_text("0" * 64 + "  METHODS_LEDGER.md\n", encoding="ascii")
            try:
                LED.LEDGER, LED.SIDE = led, side
                LED.add("METHODS_LEDGER.md", "test kind", "test decision", "test why", "test evidence", root=ROOT)
            finally:
                LED.LEDGER, LED.SIDE = old
            h, _ = _sidecar_hash(side)
            self.assertEqual(h, hashlib.sha256(led.read_bytes()).hexdigest())


if __name__ == "__main__":
    res = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    sys.exit(0 if res.wasSuccessful() else 1)
