#!/usr/bin/env python3
"""Writes AMENDMENT_A13.md (+ sidecar). Facts only. Refuses to overwrite. Written BEFORE any code change it governs."""
import hashlib, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parent.parent; OUT = ROOT / "AMENDMENT_A13.md"
assert not OUT.exists(), "exists; never overwrite"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
cited = ["SECTION5_PROTOCOL.md", "AMENDMENT_A12.md", "A12_MACHINERY_REPORT.md", "COLD_AUDIT_STATUS.md", "section5_cold_audit.md", "section5/s5_models.py", "section5/s5_a8_gate.py", "section5/s5_machinery_run.py", "section5/s5_ledger.py",
         "section5/results/a8_2_gate_RAW3_seed777.json", "section5/results/a12_machinery_RAW3.json", "D6_REPORT.md"]
now = datetime.datetime.now(datetime.timezone.utc)
L = ["# Amendment A13 to SECTION5_PROTOCOL.md (EM tolerance per observation, gate sanity check, open findings list, ledger rule)", "",
     f"Dated {now.isoformat()} UTC ({now.astimezone(ZoneInfo('America/New_York')).isoformat()} New York). Status: ADOPTED when committed with its hash sidecar; written before any code change it governs. Facts only.", "",
     "## Evidence cited (hashes before this amendment's changes)", "", "| Document | SHA-256 |", "|---|---|"]
for f in cited: L.append(f"| `{f}` | `{sha(ROOT / f)}` |")
L += ["", "## 1. EM tolerance per observation (supersedes the tolerance of A12 item 1, finding 6)", "",
      "- Why: the A12 rule (absolute change of the total training log-likelihood below 1e-4 nats, cap 200) made the full run 2.5x slower on the machinery folds (RAW 3: 9.9 to 25.8 min; LEGACY 29: 9.9 to 23.6 min) and 56 of 239 EM starts on RAW 3 (30 of 187 on LEGACY 29) reached the cap, 39 of 70 Student-t HMM starts on RAW 3 (`A12_MACHINERY_REPORT.md`). The total log-likelihood scales with the number of observations, so an absolute tolerance is a different bar for every fold and set size.",
      "- Rule: an EM run converges when |change in the total training log-likelihood| / N < 1e-6 between consecutive iterations, N = the number of real (non-skipped, non-padded) training updates in the batch; maximum 500 iterations; same rule for the Gaussian HMM, Student-t HMM and HSMM, baseline and feature models. `fit_info` records the iterations, `converged` per start and N. Cap hits are reported per family in every machinery and run report (starts at the cap / starts). 5.4 'tol 1e-4' is read as this per-observation tolerance 1e-6 from now on; the A12 statement 'absolute 1e-4 nats' is replaced.", "",
      "## 2. Gate sanity check (single seed, RAW 3 only)", "",
      "- Why: findings 6, 7, 9, 14 and 15 changed detector and splice behaviour after the A8.2 gate was run. A check that nothing broke is needed before anything else is built on the new code. It is not a re-roll of the A8-A8.4 gate decision, which stays on record.",
      "- Procedure: `s5_a8_gate.py RAW 3 777` unchanged in its rule (A8.2: P1 inside the 95% day-level bootstrap interval of P2, 8 detectors; N1 200, P1 and P2 200 each, 2,000 bootstrap replicates), run on the A13 code with an output tag so the earlier result file is not overwritten (`a13_gate_RAW3_seed777.json`). Reported as it comes: number of detectors inside, and the earlier A8.2 result (8 of 8) beside it. No second seed, no re-draw, no rule change.", "",
      "## 3. Open cold-audit findings", "",
      "- `OPEN_AUDIT_FINDINGS.md` (hashed) lists the 10 findings that are still open (10, 12, 13, 16-22), with severity and what each affects. No finding is fixed by this amendment.", "",
      "## 4. Machinery timing under the new tolerance", "",
      "- Why: the run time of the 34-fold run depends on EM iterations. `s5_machinery_run.py RAW 3` is rerun on the A13 code (tag a13; contaminated fold only, same guards) and compared with the A10 and A12 runs: runtime per stage, peak memory, cap hits per family, resume, failures. No result enters any protocol decision.", "",
      "## 5. Ledger", "",
      "- From A13 on, every ledger row carries WHY (the reason for the step) and EVIDENCE (the diagnostic, audit finding, report or literature citation). `s5_ledger.py add` requires both and refuses an empty value. Rows before A13 keep their format; new rows go in a second table of the Section 5 part with an Evidence column.",
      "- Idea for Section 6, recorded as an idea only and not pre-registered (no hypothesis, no test, no threshold is fixed): per asset, the settling time of the response after a confirmed break and the share of the total move still remaining at T_c, for price (cumulative return) versus volatility. Why recorded: H2 reads the response from T to T+30 minutes at fixed horizons, which does not say how much of the move has already happened when the alarm is confirmed. Evidence for relevance: D6 found SPY variance in the hour after FOMC statements a median 8.56 times the hour before, against 0.91 at random times (`D6_REPORT.md`), so moves continue after the event time; no analysis of settling time exists yet.", "",
      "## Governs", "", "The five items, their unit tests, the protocol re-freeze (previous text preserved as `SECTION5_PROTOCOL_v3_FROZEN_A12.md`) and ledger rows. No evaluation data, no clean fold."]
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8")); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii"); print("written", sha(OUT))
