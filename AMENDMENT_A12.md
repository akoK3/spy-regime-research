# Amendment A12 to SECTION5_PROTOCOL.md (audit findings 6, 7, 9, 14, 15; H1(c) schedule times; machinery rerun)

Dated 2026-11-03T22:01:07.299277+00:00 UTC (2026-11-03T17:01:07.299277-05:00 New York). Status: ADOPTED when committed with its hash sidecar; written before the code it governs. Facts only. `sr512.pdf` is NY Fed Staff Report 512 (Lucca and Moench, 2015, 'The Pre-FOMC Announcement Drift', J. Finance), downloaded from newyorkfed.org.

## Evidence cited (hashes before this amendment's changes)

| Document | SHA-256 |
|---|---|
| `SECTION5_PROTOCOL.md` | `ffaf286d2da930e11dd79e3cded359752e8404ab3fc8a9d60d530497c39e1c45` |
| `AMENDMENT_A6.md` | `db787ec0071b5b6c0ff4048cd281bf54e95e0c60b5f25e89fb6f02d55d5744a5` |
| `AMENDMENT_A11.md` | `297551fb2e58b1f84939e66a6b67104e4c71db6ad30bb2534a7fd5ac6235f97c` |
| `COLD_AUDIT_STATUS.md` | `e06485a5309f1e311987cd88fbd1587e11026cacb3c884adc5b838eb4168f923` |
| `section5_cold_audit.md` | `fc3b4a3fa8facb6a901b2916ecad4b9d45b407c9a23a736bfd86943d7c1fb062` |
| `section5/s5_models.py` | `8c0f9acbe0fb0a9d83e43bcf4d657518cd24114fd3ff9f2213d51c9ddbd91daf` |
| `section5/s5_events.py` | `25b3e7c713942966f26e8ec6262ab6113ee684f2bb825eae56b094735d50665e` |
| `section5/s5_sweep.py` | `dfb7fe2264df396d68c2c797f929aeeab6aeea910063cfc635c8e4d6f22f9b00` |
| `section5/s5_d2.py` | `de822812d38d1b152a179ef37cd7fc2b77a1144fadf8d97be6e8300f8d761a02` |
| `section5/s5_a6.py` | `c4706bd344f26f37a0bc717fc2360d5aba76b95a4fda53274c257b822b8c1a64` |
| `section5/results/h1c_release_times.json` | `b027614d8eedbe3b8d56c00dd133a52feac6fedaba47f0be7cdf239a84fe1f6d` |
| `section5/cache/lm_paper/sr512.pdf` | `c7cb0f335c60cb9fc305189935fb7c51e98fa8461c2b33efd51eb5a5c3f2e34b` |

## 1. Cold audit findings, each with a unit test

- **6, EM stopping.** 5.4 says tol 1e-4; the code stopped when |change in log-likelihood| < 1e-4 x max(1, |log-likelihood|). Now: stop when |change in the total training log-likelihood| < 1e-4 nats (absolute), maximum 200 iterations, for the Gaussian HMM, Student-t HMM and HSMM alike, baseline and feature models alike. `fit_info` records the iterations and whether the tolerance was reached before the cap; fits that reach the cap are reported, not hidden.
- **7, old state in the refractory period.** A6 item 1: old state = argmax at updates 1-2 and at each alarm. The code also re-based it at every real update inside the 30-minute refractory period. Now: the old state is set at the first real updates (up to the warm-up), and at each alarm to the argmax at the alarm update; it does not change during the refractory period (no alarms, count 0). Applied to the loop detector and the vectorised sweep, which must agree (unit test).
- **9, break tau range.** A6: tau on the 11:05-14:30 grid, at most 14:00 for sandwiches. The code capped every break at slot 264 (13:55). Now: permanent breaks and null splices draw tau from all grid slots 94-299 (availability 11:05-14:30); sandwiches draw tau from grid slots with availability at most 14:00 (slot at most 269) and with the first bar after the sandwich inside the session (slot at most 388 - duration): at most 269 for 30 and 60 minutes, at most 264 for 120 minutes. The constant `G_MAX = 264` and the A8 gate scripts stay as they were for the record; new splice builds use `tau_cap(duration)`.
- **14, hit window and pre-seam evidence.** A hit now requires the first update of the alarm run (T_d; for BOCPD the drop update) to be available strictly after tau, and T_c available at most 60 minutes after tau. Before: T_c at or after tau, which allowed alarms built from session A only. Feature look-back windows still contain pre-seam bars; the criterion concerns the alarm updates only.
- **15, unconfirmed alarms.** 5.5: unconfirmed by the close is dropped and counted. A candidate (HMM/HSMM: a started run with count between 1 and 2; BOCPD: a drop candidate) still open when the session ends is counted as dropped; the loop detectors return the count, the sweeps return it with `return_dropped=True`, and the backend reports, at the calibrated threshold, the share of validation sessions that end with an open candidate.
- These changes alter detector behaviour and the splice design. Results computed under the earlier code (A6/A7 pilots, A8 gates, A8.3, A8.4, A10 machinery check) are records of that code and are not re-run except as stated in item 3.

## 2. H1(c) release times without a stated time

- Source for the schedule: Lucca and Moench (2015), section 2 (`sr512.pdf`, hash above): 'From September 1994 to March 2011, FOMC statements were regularly released at, or a few minutes after, 2:15 pm following each scheduled meeting. Since April 2011, the time of the release has varied between 12:30 pm and 2:00 pm on days of FOMC meetings on which a press conference by the FOMC Chairman is held at 2:15 pm.'
- Rule, in order, for a meeting with no 'For release at' time on its statement page: (a) if the Fed's press-conference page for that meeting (federalreserve.gov/monetarypolicy/fomcpresconf<date>.htm; press-conference days are those with a 'Press Conference' link on the Fed's historical FOMC pages) states 'FOMC Meeting Statement (Released <date> at <time>)', that time is used (it overrides the schedule; e.g. a stated 12:20 is used as stated); (b) otherwise a meeting before April 2011 gets 14:15 (Lucca and Moench; 'a few minutes after' is a stated uncertainty of the window start, recorded); (c) otherwise a meeting from 2013 on gets 14:00, accepted only if every Fed page that states a time from 2013 on (statement pages and press-conference pages) states 14:00, checked and recorded; (d) a meeting from April 2011 to December 2012 that is not a press-conference day has no Fed source and no statement in Lucca and Moench: ambiguous, excluded; (e) a meeting between 2013 and the first statement page that states a time, for which (c) fails, is excluded. Every record carries its basis (stated on statement page / Fed press-conference page / schedule with source) and the excluded meetings carry their reason.
- Output `section5/results/h1c_schedule_times.json` (basis and page hashes per meeting); the eligible-event list of A8 item 2 is regenerated from the stated and the schedule times. The hit window is [t, t + 60 min].

## 3. Machinery rerun

- After items 1 and 2, the A10 machinery check is rerun on RAW fold 3 and LEGACY fold 29 (contaminated folds only; same guards), with the HSMM grid of A11 (K 2-3). Runtime, memory, failures, the number of fits that reach the 200-iteration cap, and resume are reported. No result enters any protocol decision.

## Governs

The code changes above with one unit test per finding, the schedule times, the machinery rerun, the protocol re-freeze (previous text preserved as `SECTION5_PROTOCOL_v2_FROZEN_A11.md`) and the ledger rows. No evaluation data, no clean fold.
