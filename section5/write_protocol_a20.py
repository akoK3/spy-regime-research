#!/usr/bin/env python3
"""Re-freezes SECTION5_PROTOCOL.md integrating A17, A18, A19, A19.1, A19.2, A19.3 and A20 (consolidation; A20 rule 6). Preserves the A16 text as SECTION5_PROTOCOL_v8_FROZEN_A16.md.
The canonical contamination list and its stated hash are unchanged. Refuses to run twice."""
import hashlib, datetime, shutil, re
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parent.parent; P = ROOT / "SECTION5_PROTOCOL.md"; V8 = ROOT / "SECTION5_PROTOCOL_v8_FROZEN_A16.md"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
t = P.read_text(encoding="utf-8"); assert "integrated through Amendment A16)" in t and not V8.exists()
assert sha(P) == "0b0669b5f341b3d6a660473e83850e8947b5e36da19f8323400ad36137e97fe9"
shutil.copyfile(P, V8); V8.with_suffix(".sha256").write_text(f"{sha(V8)}  {V8.name}\n", encoding="ascii")
now = datetime.datetime.now(datetime.timezone.utc)


def ed(a, b):
    global t; assert t.count(a) == 1, a[:70]; t = t.replace(a, b)


AM = [("A17", "AMENDMENT_A17.md", "reproduction of main-run fits with exact-match abort; saved models and alarms; H1(c); POST HOC R=1-net H1(a); test QLIKE percent; POST_MAIN_RUN category"),
      ("A18", "AMENDMENT_A18.md", "pre-registered sensitivity: selection by one-step-ahead predictive log-likelihood"),
      ("A19", "AMENDMENT_A19.md", "D8 census, D7 non-volatility response test, Step 2, daily-VIX extension, 5.10 robustness and 5.11 power definitions"),
      ("A19.1", "AMENDMENT_A19_1.md", "D8b sensitivity"),
      ("A19.2", "AMENDMENT_A19_2.md", "D7 jump sizes, threshold-sweep scoring, ratio 3 and 5.29 positive control"),
      ("A19.3", "AMENDMENT_A19_3.md", "D7 bar-scaling check, jumps sized from the post-tau window, stop rule"),
      ("A20", "AMENDMENT_A20.md", "__sadj-only scale inputs, deseasonalised QLIKE target, MR1 superseded by MR2, re-freeze")]
ed("(integrated through Amendment A16)", "(integrated through Amendment A20)")
t = re.sub(r"Re-frozen with A16 \S+ UTC \(\S+ New York; ", f"Re-frozen with A17-A20 {now.isoformat()} UTC ({now.astimezone(ZoneInfo('America/New_York')).isoformat()} New York; ", t, count=1)
ed("and with A15 at 2026-11-04T01:25 UTC)", "and with A15 at 2026-11-04T01:25 UTC and with A16 at 2026-11-04T01:38 UTC)")
ed("Amendments A6 to A16. ", "Amendments A6 to A20. ")
ed("through A15 as `SECTION5_PROTOCOL_v7_FROZEN_A15.md` (sha256 `a86cf099dfd6ed7af416fc2603a6951c18ce3e7fdf659a76599bf4f14bee5ea1`)",
   f"through A15 as `SECTION5_PROTOCOL_v7_FROZEN_A15.md` (sha256 `a86cf099dfd6ed7af416fc2603a6951c18ce3e7fdf659a76599bf4f14bee5ea1`), through A16 as `{V8.name}` (sha256 `{sha(V8)}`)")
ed("\n\nSupporting records", "\n" + "\n".join(f"| {a} | `{f}` | {s} | `{sha(ROOT / f)}` |" for a, f, s in AM) + "\n\nSupporting records")
ed("5.2 Pools: primary 19 (both eras); sensitivity 80 (RAW only;", "5.2 Pools: primary 19 (both eras), narrowed by A20 rule 1 to 13 detector inputs (scale-type columns, name-stem families rv, downside, abs_return, intrabar_range, only in their `__sadj` versions: return_1m, relative_volume20, momentum5/10/15/30_endpoint, close_location_proxy and the six `__sadj` columns); sensitivity 80 (RAW only; the same A20 rule applies;")
ed("QLIKE: regime-conditional forecast of next-60-min variance,", "QLIKE: regime-conditional forecast of next-60-min variance (A20 rule 2: the target is deseasonalised, (60/n) times the sum over the next 60 one-minute bars of r^2 divided by the causal slot baseline of 5.6, n >= 50 finite),")
ed("\n## Open items", """
5.17 A17 (after the main run): deterministic reproduction of the main-run fits with exact-match abort (exit 4), saved models and test alarm times, A7 fold-level thresholds, H1(c) as pre-registered, the POST HOC R=1-net H1(a) (200 placebo splices, seed 777) and the test-segment QLIKE percent; contamination category POST_MAIN_RUN.

5.18 A18 (pre-registered sensitivity): 5.8 selection with the mean negative one-step-ahead predictive log-likelihood of the next 5-min return as objective; volatility families rv, downside, abs_return, intrabar_range; does not replace the 5.8 setups or H1 verdicts.

5.19 A19 to A19.3 (secondary and descriptive): D8 census of non-volatility changes (60-min windows; 'large' at the i.i.d. 1% points; 'occurs' = P(large given variance-stable) >= 0.02 in both eras) and D8b sensitivity (A19.1); D7 variance-neutral liquidity / trend / momentum / jump injections after tau on stable test days of the confirmatory folds, scored by threshold sweep (mean hit-rate gain over alarm rates 0-0.5 versus the matched null; 'responds' = gain >= 0.10 with a day-clustered 95% CI excluding 0; A19.2), jumps 2 x 4 and 2 x 5 sd of the post-tau window (A19.3), gates (i) variance neutrality, (ii) positive control at variance ratios 3 and 5.29, (iii) null hit rate <= 0.30, (iv) >= 100 days; Step 2 (type-matched detectors) only for types D7 misses and D8 shows occur; daily-VIX extension (previous close); 5.10 threshold +/-0.05 = A7 target 0.2 +/- 0.05 alarms per session; 5.11 power via `s5_stats.mde`.

5.20 A20: scale-type inputs only as `__sadj` (5.2) and a deseasonalised QLIKE target (5.6), motivated by the D7 diagnostic on RAW 3 (feature-model states tracked the time of day). The main run of 2026-11-04/05 (`section5/results/main_run/`) is MR1, superseded and kept as a record; MR2 (`section5/results/main_run_2/`, all 34 folds) followed by the A17-style phase and D7 per A19.3 on its fits replaces it. The 26 / 8 fold split and the canonical list are unchanged; every fold's test segment was scored in MR1, so MR2's fold tests are development evidence; 5.13 remains confirmatory.

## Open items""")
P.write_text(t, encoding="utf-8"); P.with_suffix(".sha256").write_text(f"{sha(P)}  {P.name}\n", encoding="ascii"); print("protocol", sha(P))
