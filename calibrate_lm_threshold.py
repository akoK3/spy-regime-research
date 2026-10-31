#!/usr/bin/env python3
"""A4 F3: calibrate the Lee-Mykland threshold by simulation. Writes a4_lm_threshold_calibration.json (+ .sha256). Refuses to overwrite.

Independent normal returns, 390-bar sessions (slot 0 has no return), unchanged statistic
stat_t = r_t / sqrt((pi/2) * sum of the 59 adjacent products |r_i||r_(i-1)| over the 60 prior returns / 59), rows t = 61..389.
Threshold = 99th percentile of max_t |stat_t| over 200,000 sessions (seed 43105), rounded to 4 decimals, with a rank-based 95% CI.
Check: a second seed (43106, 200,000 sessions) must give a false-alarm rate between 0.9% and 1.1% at the rounded threshold.
"""
import json, hashlib, datetime
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "section431_step3_all_in_one_results" / "a4_lm_threshold_calibration.json"
N, CHUNK, L = 200_000, 5_000, 390
T = np.arange(61, 390)  # rows 61..389


def session_max(seed, n):
    rng = np.random.default_rng(seed)
    out = np.empty(n)
    for a in range(0, n, CHUNK):
        m = min(CHUNK, n - a)
        r = rng.standard_normal((m, L - 1))              # column c holds slot c+1
        ab = np.abs(r)
        p = ab[:, 1:] * ab[:, :-1]                       # p[:, j] = |r slot j+2| * |r slot j+1|
        cs = np.concatenate([np.zeros((m, 1)), np.cumsum(p, axis=1)], axis=1)
        s59 = cs[:, T - 2] - cs[:, T - 61]               # 59 adjacent pairs among slots t-60..t-1
        stat = r[:, T - 1] / np.sqrt((np.pi / 2) * s59 / 59)
        out[a:a + m] = np.abs(stat).max(axis=1)
    return out


def main():
    assert not OUT.exists(), "calibration exists; never overwrite"
    m1 = np.sort(session_max(43105, N))
    c = float(np.quantile(m1, 0.99))
    sd = np.sqrt(N * 0.99 * 0.01)
    lo, hi = float(m1[int(N * 0.99 - 1.96 * sd)]), float(m1[int(N * 0.99 + 1.96 * sd)])
    thr = round(c, 4)
    m2 = session_max(43106, N)
    rate2, rate1 = float((m2 > thr).mean()), float((m1 > thr).mean())
    rate_old, rate_audit = float((m2 > 5.4667).mean()), float((m2 > 4.36).mean())
    ok = 0.009 <= rate2 <= 0.011
    doc = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), amendment="4.3-A4 F3",
               design="independent normal returns; 390-bar sessions; max |stat| over rows 61-389; 99th percentile",
               sessions=N, seeds=[43105, 43106], threshold=thr, threshold_unrounded=c, ci95_rank_based=[lo, hi],
               false_alarm_rate_at_threshold=dict(seed_43105=rate1, seed_43106=rate2), check_second_seed_between_0_9_and_1_1_pct="PASS" if ok else "FAIL",
               old_threshold_5_4667_false_alarm_rate_seed_43106=rate_old, audit_threshold_4_36_false_alarm_rate_seed_43106=rate_audit,
               script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    data = (json.dumps(doc, indent=2) + "\n").encode("utf-8")
    OUT.write_bytes(data)
    OUT.with_suffix(".sha256").write_text(f"{hashlib.sha256(data).hexdigest()}  {OUT.name}\n", encoding="ascii")
    print(json.dumps({k: doc[k] for k in ("threshold", "ci95_rank_based", "false_alarm_rate_at_threshold", "check_second_seed_between_0_9_and_1_1_pct",
                                          "old_threshold_5_4667_false_alarm_rate_seed_43106", "audit_threshold_4_36_false_alarm_rate_seed_43106")}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
