#!/usr/bin/env python3
"""Tests for s5_hf_cleaning_check.py on synthetic Raw / Clean files (no market data)."""
import sys, json, tempfile, unittest
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_hf_cleaning_check as C


def synth(tmp, mode, seed=0, n_days=40):
    rng = np.random.default_rng(seed); rows = []; spikes, randoms = set(), set()
    for d in pd.bdate_range("2023-01-03", periods=n_days):
        ts = pd.date_range(d + pd.Timedelta(hours=9, minutes=30), periods=390, freq="min"); lc = np.log(400) + np.cumsum(rng.normal(0, 4e-4, 390)); c = np.exp(lc)
        for i in rng.choice(np.arange(10, 380), 6, replace=False):
            c[i] *= np.exp(rng.choice([-1, 1]) * 3e-3); spikes.add(ts[i])                    # isolated spike: the move into bar i reverts in bar i + 1
        for i in rng.choice(np.arange(10, 380), 6, replace=False):
            if ts[i] not in spikes: randoms.add(ts[i])
        for t, x in zip(ts, c): rows.append(dict(datetime=t, Open=x, High=x * 1.0002, Low=x * 0.9998, Close=x, Volume=100, source="iex"))
    raw = pd.DataFrame(rows); drop = spikes if mode == "spikes" else randoms
    clean = raw[~raw["datetime"].isin(drop)].copy(); clean.loc[clean.index[5], "Volume"] = 101      # one changed bar
    p_raw, p_clean = Path(tmp) / "SPY_raw_1min_2026-11-11.csv", Path(tmp) / "SPY_clean_1min_2026-11-11.csv"
    raw.to_csv(p_raw, index=False); clean.to_csv(p_clean, index=False); return p_raw, p_clean, len(drop)


class Test(unittest.TestCase):
    def run_check(self, mode):
        with tempfile.TemporaryDirectory() as td:
            pr, pc, n = synth(td, mode); sys.argv = ["x", "--raw", str(pr), "--clean", str(pc), "--out", td]
            self.assertEqual(C.main(), 0); return json.loads((Path(td) / "hf_cleaning_spy.json").read_text()), n

    def test_counts_and_reversal_detected_for_centered_spike_filter(self):
        r, n = self.run_check("spikes"); c = r["counts"]
        self.assertEqual(c["removed"], n); self.assertEqual(c["added"], 0); self.assertEqual(c["changed"], 1); self.assertEqual(c["changed_by_field"]["Volume"], 1)
        self.assertEqual(c["removed_by_documented_step"], {"8_or_unexplained": n})
        k1 = r["reversal"]["removed_all"]["by_k"]["1"]["reversal"]; self.assertGreater(k1["difference"], 0.3); self.assertGreater(k1["ci95"][0], 0)

    def test_no_reversal_excess_for_random_removals(self):
        r, n = self.run_check("random"); k1 = r["reversal"]["removed_all"]["by_k"]["1"]["reversal"]
        self.assertLess(abs(k1["difference"]), 0.15); self.assertLess(k1["ci95"][0], 0.0 + 1e-9)

    def test_refuses_study_inputs_and_mixed_releases(self):
        sys.argv = ["x", "--raw", str(C.STUDY_INPUTS[1]), "--clean", str(C.STUDY_INPUTS[0])]
        with self.assertRaises(SystemExit): C.main()
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td) / "hfdatalibrary_raw_1min_1tickers_2026-11-11.zip", Path(td) / "hfdatalibrary_clean_1min_1tickers_2026-11-12.zip"; a.write_bytes(b""); b.write_bytes(b"")
            sys.argv = ["x", "--raw", str(a), "--clean", str(b), "--out", td]
            with self.assertRaises(SystemExit) as cm: C.main()
            self.assertIn("different releases", str(cm.exception))


if __name__ == "__main__": unittest.main()
