#!/usr/bin/env python3
"""A11 item 1: era-level threshold for 5.13. For one era with n TRAIN sessions: the frozen final setup is fitted on sessions [0, n-63), sessions [n-63, n-58) are the 5-session embargo,
and the last 58 sessions are native calibration sessions on which the A7 rule (bisection to 0.2 alarms per session) sets the threshold; the threshold is then frozen and used with the full-TRAIN
refit. EraBackend reuses DataBackend with that split ('train' = fit sessions, 'val' = calibration sessions, no test segment). It reads TRAIN data only (load_era asserts it) and is not run here."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_backend as BK, s5_lib as L

N_CAL = 58; EMBARGO = 5; MIN_FIT = 100


def era_split(n, n_cal=N_CAL, embargo=EMBARGO):
    """Session indices (fit, embargo, calibration) of an era with n TRAIN sessions."""
    if n < n_cal + embargo + MIN_FIT: raise ValueError(f"{n} sessions: too few for {n_cal} calibration + {embargo} embargo + {MIN_FIT} fit sessions")
    return np.arange(0, n - n_cal - embargo), np.arange(n - n_cal - embargo, n - n_cal), np.arange(n - n_cal, n)


class EraBackend(BK.DataBackend):
    def __init__(self, era):
        if era not in ("LEGACY", "RAW"): raise ValueError(era)
        self.era, self.fold, self.id = era, -1, f"{era}|ERA"; self.min_days = 8; self._ctx = None; self._fits = {}; self._seqs = {}; self._splice = None

    def _segments(self, d):
        fit, emb, cal = era_split(len(d["first"])); return dict(train=fit, val=cal, test=np.array([], int), embargo=emb)

    def calibrate(self, family, setup):
        """Threshold of the final setup on the calibration sessions (A7 rule), with the split recorded."""
        r = self.final_thresholds(self.era, family, setup); c = self.c; seg = c["seg"]; d = c["d"]; day = lambda i: str(d["day"][d["first"][int(i)]])
        r.update(fold="ERA", n_fit=len(seg["train"]), n_embargo=len(seg["embargo"]), n_calibration=len(seg["val"]), fit_last_day=day(seg["train"][-1]), calibration_first_day=day(seg["val"][0]), calibration_last_day=day(seg["val"][-1]),
                 numeric_era_threshold="set here (A11 item 1)")
        return r
