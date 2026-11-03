#!/usr/bin/env python3
"""H1 scoring logic (A6/A7/A8): per-fold paired effects and the per-family decision. Pure functions on stored curves and losses; no data access.
(a) H1(a): partial area (A6 item 2) of the hit-rate curve vs null alarm rate, features minus baseline; folds with fewer than 8 stable test days are skipped (A8 item 3).
(b) H1(b): next-60-min QLIKE, baseline mean loss minus feature mean loss (positive = features better), with the Diebold-Mariano statistic reported per fold.
(c) H1(c) (secondary) lives in s5_h1c.py. Confirmatory folds exclude the contaminated ones (A8 item 2); the all-folds analysis is the sensitivity."""
import numpy as np
import s5_a6 as A
import s5_eval as V
import s5_stats as ST

MIN_STABLE_TEST_DAYS = 8
FAMILIES = ("gaussian_hmm", "student_t_hmm", "hsmm", "bocpd")


def h1a_fold_effect(points_feat, points_base, n_stable_test):
    """pAUC(features) - pAUC(baseline) on one fold; None (skipped, with the reason) if the fold has fewer than 8 stable test days."""
    if n_stable_test < MIN_STABLE_TEST_DAYS: return dict(effect=None, skipped=f"{n_stable_test} < {MIN_STABLE_TEST_DAYS} stable test days")
    return dict(effect=float(A.pauc(points_feat) - A.pauc(points_base)), skipped=None)


def h1b_fold_effect(loss_base, key_base, loss_feat, key_feat, lag=12):
    """Align the two loss series on common decision bars (same session and slot), then mean(base) - mean(feat) and the DM test."""
    lb, lf, common = V.align(np.asarray(loss_base, float), np.asarray(key_base), np.asarray(loss_feat, float), np.asarray(key_feat))
    ok = np.isfinite(lb) & np.isfinite(lf); lb, lf = lb[ok], lf[ok]
    if len(lb) == 0: return dict(effect=None, dm=None, n=0, skipped="no common scored bars")
    return dict(effect=float(lb.mean() - lf.mean()), dm=V.diebold_mariano(lb, lf, lag), n=int(len(lb)), skipped=None)


def family_result(effects_a, effects_b, fold_ids, excluded=(), nboot=10000, seed=0):
    """effects_a / effects_b: lists over fold_ids (consecutive fold order; None = skipped or not evaluable). Confirmatory = folds not in `excluded`; sensitivity = all folds.
    Fold-level tests per component (5.9) and the IU p-value of the two block-bootstrap p-values."""
    out = {}
    for label, keep in (("confirmatory", [f not in set(excluded) for f in fold_ids]), ("all_folds_sensitivity", [True] * len(fold_ids))):
        xa = [e for e, k in zip(effects_a, keep) if k and e is not None]; xb = [e for e, k in zip(effects_b, keep) if k and e is not None]
        ta, tb = ST.fold_tests(xa, nboot=nboot, seed=seed), ST.fold_tests(xb, nboot=nboot, seed=seed + 1)
        out[label] = dict(H1a=ta, H1b=tb, p_iu=ST.intersection_union(ta["p_block_bootstrap"], tb["p_block_bootstrap"]))
    return out


def h1_decision(family_results, alpha=0.05, which="confirmatory"):
    """Holm across the four families on the IU p-values (5.11)."""
    return ST.holm({f: family_results[f][which]["p_iu"] for f in family_results}, alpha)
