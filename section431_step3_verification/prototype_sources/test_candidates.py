"""Independent construction and leakage checks; stdlib unittest only."""
import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
from section4_3_1_candidates import construct, feature_warmup, verify_prefix, load_development


def sample(lengths=(390,)*24):
    rng = np.random.default_rng(4816)
    slot = np.concatenate([np.arange(n) for n in lengths])
    day = np.concatenate([np.repeat(f"day{i:02}", n) for i, n in enumerate(lengths)])
    first = np.r_[0, np.cumsum(lengths)[:-1]]
    end = np.cumsum(lengths)
    close = np.exp(np.cumsum(rng.normal(0, .001, len(slot))))*100
    r = np.full(len(slot), np.nan)
    j = np.flatnonzero(slot > 0)
    r[j] = np.log(close[j]/close[j-1])
    return dict(era="TEST", r=r, valid=np.isfinite(r), close=close, day=day, slot=slot,
                range=np.repeat(.002, len(slot)), volume=np.repeat(100., len(slot)), first=first, end=end)


class CandidateTests(unittest.TestCase):
    def test_loader_date_endpoints_and_availability(self):
        t = pd.date_range("2024-12-31T14:30:00Z", periods=390, freq="min")
        close = 100*np.exp(np.arange(390)*.0001)
        p = pd.DataFrame({"utc_minute_start_assumed":t,
            "available_utc_assuming_minute_start":t+pd.Timedelta(minutes=1),
            "session_date_ny":"2024-12-31", "minute_index_in_session":np.arange(390),
            "source_epoch":"RAW", "SPY_log_return_1m":np.r_[np.nan,np.log(close[1:]/close[:-1])],
            "SPY_return_eligible":np.r_[0,np.ones(389)]})
        e = pd.DataFrame({"utc_minute_start":t, "session_date_ny":"2024-12-31",
            "Close":close, "High":close+.01, "Low":close-.01,
            "Volume":100., "numeric_ohlcv_valid":1})
        spec = dict(first_session="2024-12-31", last_session="2024-12-31", panel_file="p", etf_file="e")
        with patch("section4_3_1_candidates.selected_csv", side_effect=[p,e]):
            d = load_development("RAW", spec)
        self.assertEqual(d["day"][0], "2024-12-31")
        self.assertEqual(d["day"][-1], "2024-12-31")
        self.assertEqual(d["available"][0]-d["t"][0], 60_000_000_000)

    def test_independent_formulas_every_window(self):
        d = sample((390, 210))
        f, _ = construct(d)
        for t in [90, 390+90]:
            for w in [5, 10, 15, 30, 60]:
                r = d["r"][t-w+1:t+1]
                self.assertAlmostEqual(f[f"rv{w}_strict"][t], np.sqrt(np.sum(r*r)), places=13)
                self.assertAlmostEqual(f[f"downside{w}_strict"][t], np.sqrt(np.sum(np.minimum(r, 0)**2)), places=13)
                self.assertAlmostEqual(f[f"momentum{w}_strict"][t], np.log(d["close"][t]/d["close"][t-w]), places=13)
            e = d["close"][t-np.arange(0, 61, 5)]
            self.assertAlmostEqual(f["rv60_sampled5_exact"][t], np.sqrt(np.sum(np.diff(np.log(e))**2)), places=13)
            past = d["r"][t-60:t]
            med = np.median(past)
            scale = 1.4826*np.median(np.abs(past-med))
            self.assertAlmostEqual(f["shock_prior60_mad"][t], (d["r"][t]-med)/scale, places=13)

    def test_missing_price_endpoints_and_partial_proxy(self):
        d = sample((390,))
        d["close"][50] = np.nan
        d["r"][[50, 51]] = np.nan
        d["valid"] = np.isfinite(d["r"])
        f, _ = construct(d)
        self.assertTrue(np.isnan(f["rv15_strict"][60]))
        self.assertTrue(np.isnan(f["rv15_partial90"][60]))  # 13 < ceil(.9*15)
        x = d["r"][60-60+1:61]
        self.assertAlmostEqual(f["rv60_partial90"][60], np.sqrt(np.nansum(x*x)*60/58), places=13)
        self.assertAlmostEqual(f["momentum15_endpoint"][60], np.log(d["close"][60]/d["close"][45]), places=13)
        self.assertTrue(np.isnan(f["rv60_sampled5_exact"][60]))  # endpoint 50 missing

    def test_session_and_halfday_reset(self):
        d = sample((390, 210, 390))
        f, _ = construct(d)
        for name, values in f.items():
            self.assertFalse(np.isfinite(values[d["slot"] < feature_warmup(name)]).any(), name)
        self.assertEqual(len(f["return_1m"]), 990)
        self.assertTrue(np.isnan(f["rv60_strict"][390+59]))
        self.assertTrue(np.isfinite(f["rv60_strict"][390+60]))

    def test_volume_prior_sessions_and_future_changes(self):
        d = sample()
        d["volume"][d["first"][20]:d["end"][20]] = 200.
        f, q = construct(d)
        self.assertEqual(f["relative_volume20"][d["first"][20]+50], 2.)
        self.assertEqual(q["relative_volume_prior_count"][d["first"][20]+50], 20)
        self.assertTrue(np.isnan(f["relative_volume20"][d["first"][9]+50]))
        cut = d["first"][21]+150
        verify_prefix(d, f, cut)
        altered = {k: v.copy() if isinstance(v, np.ndarray) else v for k, v in d.items()}
        for k in ["r", "close", "range", "volume"]:
            altered[k][cut:] *= 1000
        g, _ = construct(altered)
        for name in f:
            np.testing.assert_allclose(f[name][:cut], g[name][:cut], atol=0, rtol=0, equal_nan=True)

    def test_zero_scale_and_volume_zero(self):
        d = sample()
        d["r"][d["valid"]] = 0.
        d["volume"][d["first"][20]+80] = 0.
        f, _ = construct(d)
        self.assertFalse(np.isfinite(f["shock_prior60_mad"]).any())
        self.assertEqual(f["rv15_strict"][70], 0.)
        t = d["first"][20]+80
        self.assertEqual(f["relative_volume20"][t], 0.)
        self.assertTrue(np.isnan(f["log_relative_volume20"][t]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
