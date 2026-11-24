#!/usr/bin/env python3
"""A15 rule 5: the main-run backend for s5_run.run_all and s5_run.freeze_step. All 34 folds in consecutive order (LEGACY 0-29, RAW 0-3, the order of the A4 folds CSV); one fold backend
in memory at a time, one era panel shared by the folds of that era. Clean folds are served only with the sha256 of the FROZEN protocol (checked here and again by every fold backend).
Era-level thresholds (A11 item 1) come from EraBackend.calibrate, which needs the completion record run_all writes after every fold is selected and scored (A16 rule 1; the
calibration fits on sessions of every fold's test segment and writes the lock that blocks any later scoring, A16 rule 5). Not run under A15. Usage (after the protocol is frozen):
  b = MainBackend(protocol_sha256); s = s5_run.run_all(b, OUT); s5_run.freeze_step(b, s, RESULTS, AMENDMENTS)"""
import sys, gc
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_backend as BK, s5_era_threshold as ET, s5_lib as L, s5_guard as G


class MainBackend:
    kind = "main"

    def __init__(self, protocol_sha256):
        self.protocol_sha256 = G.verify_frozen_protocol(protocol_sha256); G.canonical_contamination()
        ft = pd.read_csv(L.R / "a4_development_nested_folds_TRAIN.csv"); self.ids = [f"{e}|{int(f)}" for e, f in zip(ft.era, ft.fold)]
        assert self.ids == G.MAIN_FOLDS, "unexpected fold table order"
        self._era = None; self._cur = None; self._era_b = None

    def _ctx(self, era):
        if self._era is None or self._era["era"] != era:
            self._cur = self._era_b = self._era = None; gc.collect(); self._era = BK.era_context(era)
        return self._era

    def _b(self, fold):
        if self._cur is None or self._cur.id != fold:
            era, n = fold.split("|"); self._cur = None; gc.collect()
            self._cur = BK.DataBackend(era, int(n), allowed=set(self.ids), protocol_sha256=self.protocol_sha256, shared=self._ctx(era))
        return self._cur

    def folds(self): return list(self.ids)
    def candidates(self, fold): return self._b(fold).candidates(fold)
    def param_grid(self, family): return BK.BOCPD_GRID if family == "bocpd" else BK.HSMM_GRID if family == "hsmm" else BK.HMM_GRID
    def objective(self, fold, family): return self._b(fold).objective(fold, family)
    def score(self, fold, family, setup): return self._b(fold).score(fold, family, setup)
    def era_thresholds(self, era, family, setup, completion):
        """A16 rule 1: EraBackend verifies the completion record written by run_all; there is no flag to set."""
        if self._era_b is None or self._era_b.era != era or self._era_b.completion != Path(completion):
            ctx = self._ctx(era); self._cur = None; self._era_b = ET.EraBackend(era, completion, self.protocol_sha256, shared=ctx)
        return self._era_b.calibrate(family, setup)

    def input_hashes(self): return BK.freeze_input_hashes()
