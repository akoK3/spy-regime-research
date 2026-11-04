#!/usr/bin/env python3
"""Integrates AMENDMENT_A15 into SECTION5_PROTOCOL.md (consolidation only), applies the A15 rule 7 reclassification to the audit status files (previous versions preserved), preserves the
A14.2 protocol as SECTION5_PROTOCOL_v6_FROZEN_A14_2.md. Refuses to run twice."""
import hashlib, datetime, shutil, re, json
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parent.parent; P = ROOT / "SECTION5_PROTOCOL.md"; V6 = ROOT / "SECTION5_PROTOCOL_v6_FROZEN_A14_2.md"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert "integrated through Amendment A14.2" in P.read_text(encoding="utf-8"); assert not V6.exists()
cl = json.loads((ROOT / "section5/results/contamination_list.json").read_text()); ex = sorted((e["era"], e["fold"]) for e in cl["folds"] if e["excluded"])
assert ex == [("LEGACY", 23), ("LEGACY", 24), ("LEGACY", 27), ("LEGACY", 28), ("LEGACY", 29), ("RAW", 1), ("RAW", 2), ("RAW", 3)] and cl["n_h1c_events"] == 98


def keep(src, dst): shutil.copyfile(ROOT / src, ROOT / dst); (ROOT / dst).with_suffix(".sha256").write_text(f"{sha(ROOT / dst)}  {dst}\n", encoding="ascii")


keep("SECTION5_PROTOCOL.md", V6.name); keep("COLD_AUDIT_STATUS.md", "COLD_AUDIT_STATUS_v4_A14_2.md"); keep("OPEN_AUDIT_FINDINGS.md", "OPEN_AUDIT_FINDINGS_v3_A14_2.md")
now = datetime.datetime.now(datetime.timezone.utc); A2 = f"`section5_cold_audit_2.md` (sha256 `{sha(ROOT / 'section5_cold_audit_2.md')}`)"


def side(path): (ROOT / path).with_suffix(".sha256").write_text(f"{sha(ROOT / path)}  {Path(path).name}\n", encoding="ascii")


# ---------- COLD_AUDIT_STATUS.md (audit 1 reclassified; audit 2 added)
cs = (ROOT / "COLD_AUDIT_STATUS.md").read_text(encoding="utf-8").split("\n")
def row(n, new):
    i = next(k for k, l in enumerate(cs) if l.startswith(f"| {n} |")); cs[i] = new
row(3, "| 3 | High | Evidence sits inside earlier folds' test blocks | **resolved** | A8 item 2: sessions touched by any pilot or diagnostic are listed mechanically; folds whose test segment intersects the list are excluded from confirmatory H1; all-folds sensitivity reported. Reopened by cold audit 2 (the first audit's LEGACY 25 run was unregistered; the registry test could not fail) and resolved by A15 rules 2-3: 8 of 34 folds excluded (LEGACY 23, 24 added), `check_registry` unit-tested to fail on an unregistered script. |")
row(6, "| 6 | Medium | EM stopping is relative, not the 1e-4 of 5.4 | **resolved** | A12 finding 6 (absolute tolerance on the total training log-likelihood, cap recorded), as amended by A13 item 1: an EM run converges when the change of the total log-likelihood divided by the number of real training updates is below 1e-6; cap 500 iterations; `fit_info.converged`; unit-tested. A12 machinery rerun (under the A12 rule): of 239 EM starts on RAW 3, 56 reached the cap; of 187 on LEGACY 29, 30. |")
row(11, "| 11 | High | Checkpoint keys omit the code version | **resolved** | Reopened by cold audit 2 (the version hashed 7 files and missed the model, event, sweep and backend code; A12 and A13 shared a version) and resolved by A15 rule 4: version = hash of every result-affecting module (import closure) with scheme tag A15, keys carry backend kind and budget; unit-tested. |")
row(12, "| 12 | Low | '25 of 25 checks' overstates coverage | **open** | Record only (A15 rule 7: Medium to Low). No change made to those checks; no test checks the splice builder for leakage. |")
row(16, "| 16 | Low | Seeds, versions and shares not recorded | **open** | Partly: run summaries record the code version; seeds, library versions and abstention/skip shares are not recorded, nor (A15 rule 7, wider scope) flagged Student-t fit counts and EM cap hits. |")
row(17, "| 17 | Medium | Input hashes not checked at run time | **open** | A15 rule 7: Low to Medium. The freeze now records the hashes of the protocol, every integrated amendment, the cited inputs and the market-data files (A15 rule 6c); data files are still not verified against them when loaded. |")
row(19, "| 19 | Low | A bad Student-t start can win silently | **resolved** | A14 (reporting) and A14.2 (rule): the kept fit is the highest-likelihood start among those satisfying the 1% rule; if none does, the best fit is kept and flagged; flagged fits are counted and an H1 sensitivity excludes folds with flagged Student-t fits; unit-tested. Low residual (cold audit 2 finding 10): when all 10 attempts of a start fail, the last attempt, not the best, is kept for that start. |")
t = "\n".join(cs)
def ed(a, b):
    global t; assert t.count(a) == 1, a[:60]; t = t.replace(a, b)
ed("updated by `AMENDMENT_A12.md`", "updated by `AMENDMENT_A12.md` and later amendments, last by `AMENDMENT_A15.md` (the A14.2 version is preserved as `COLD_AUDIT_STATUS_v4_A14_2.md`; earlier ones as v1-v3)")
ed("Still open: 10, 12, 13, 16-18, 20, 21; disclosed: 1 (residual), 2, 4 (gap handling), 5, 8.", "Reopened and resolved by A15: 3, 11. Still open: 10, 13, 17 (Medium), 12, 16, 18, 20, 21 (Low); disclosed: 1 (residual), 2, 5, 8; resolved with a disclosed remainder: 4 (gap handling).")
t += ("\n\n## Cold audit 2 (" + A2 + ", 15 findings; A15)\n\nTotals: resolved 9, open 6.\n\n| # | Severity | Finding | Status | Evidence |\n|---|---|---|---|---|\n"
      "| 1 | Critical | Baseline never tuned; inherits the feature model's K/lambda | **resolved** | A15 rule 1: baseline tuned on validation with the identical grid, 3 starts and tie rule (`base_params`); unit-tested. |\n"
      "| 2 | High | LEGACY 23 and 24 in the confirmatory set | **resolved** | A15 rule 2: audit-1 scripts registered; regenerated list: 8 excluded, 26 confirmatory, 98 H1(c) events; unit-tested. |\n"
      "| 3 | High | Registry test could not fail; 3 scripts unregistered | **resolved** | A15 rule 3: `check_registry` (plain pattern, backend constructors included), shown to fail on an unregistered script; scripts registered. |\n"
      "| 4 | High | Checkpoint version omits model, event, sweep, backend code | **resolved** | A15 rule 4 (see audit 1 finding 11). |\n"
      "| 5 | High | No main-run path; freeze thresholds not era-level | **resolved** | A15 rule 5: `s5_main.MainBackend`, clean folds only with the frozen-protocol hash, era thresholds via `EraBackend` after a complete run, `run_all` loads the contamination list; unit-tested without data. |\n"
      "| 6 | Medium | Holm drops a non-evaluable family from m | **resolved** | A15 rule 6a: missing p enters as 1; unit-tested. |\n"
      "| 7 | Medium | Failed H1(a) splice construction recorded as a zero effect | **resolved** | A15 rule 6b: recorded as a failure with its reason, listed in reports; unit-tested. |\n"
      "| 8 | Medium | Freeze records no data-input hashes and no amendment after A10 | **resolved** | A15 rule 6c; unit-tested. |\n"
      "| 9 | Medium | 5.14 unbounded for label-free statistics | **resolved** | A15 rule 6d: label-free analyses do not touch sessions; unit-tested. |\n"
      "| 10 | Low | Student-t keeps the last attempt when all 10 fail | **open** | No change. |\n"
      "| 11 | Low | Greedy adds features on non-finite QLIKE | **open** | No change. |\n"
      "| 12 | Low | Block bootstrap crosses the era boundary | **open** | No change; extends the disclosed remainder of audit 1 finding 4. |\n"
      "| 13 | Low | Flagged-fit counts and EM cap hits missing from run_summary.json | **open** | No change (see audit 1 finding 16). |\n"
      "| 14 | Low | Feature caches have no version key | **open** | No change. |\n"
      "| 15 | Low | 5.16 overstates the backend session guard | **open** | No change. |\n")
(ROOT / "COLD_AUDIT_STATUS.md").write_text(t, encoding="utf-8"); side("COLD_AUDIT_STATUS.md")

# ---------- OPEN_AUDIT_FINDINGS.md (rewritten; A14.2 list preserved)
of = (ROOT / "OPEN_AUDIT_FINDINGS.md").read_text(encoding="utf-8").split("\n"); keep_rows = {l.split("|")[1].strip(): l for l in of if re.match(r"\| \d+ \|", l)}
keep_rows["12"] = keep_rows["12"].replace("| 12 | Medium |", "| 12 | Low |")
keep_rows["16"] = keep_rows["16"].rstrip(" |") + " A15 (wider scope): flagged Student-t fit counts and EM cap hits are not in `run_summary.json` either. |"
keep_rows["17"] = "| 17 | Medium | Input hashes not verified at run time (`s5_lib.py:58,149,112-117`) | Data provenance: the freeze records the hashes of the protocol, every integrated amendment, the cited inputs and the market-data files (A15 rule 6c), but the loaders do not verify the data files against them; a silent change of a data file between runs would not be caught. |"
order = ["10", "12", "13", "16", "17", "18", "20", "21"]
O = ["# Open cold-audit findings after A15 (earlier lists preserved as `OPEN_AUDIT_FINDINGS_v1_A13.md`, `_v2_A14.md`, `_v3_A14_2.md`)", "",
     f"Written {now.isoformat()} UTC. Sources: `section5_cold_audit.md` (audit 1), {A2} (audit 2), `COLD_AUDIT_STATUS.md`. Reclassified by `AMENDMENT_A15.md` rule 7. Facts only.", "",
     "## Audit 1", "", "Eight findings are open: 3 Medium (10, 13, 17), 5 Low (12, 16, 18, 20, 21). Findings 3 and 11 were reopened by audit 2 and resolved by A15. None changes the primary H1 detection or QLIKE computation.", "",
     "| # | Severity | Finding | What it affects |", "|---|---|---|---|"] + [keep_rows[k] for k in order] + [
     "", "Disclosed (problem remains, stated in a dated record): 1 (residual: the R=1 gate failed on LEGACY 29, protocol 5.15), 2, 5, 8; resolved with a disclosed remainder: 4 (gap handling in the block bootstrap).", "",
     "## Audit 2", "", "Six findings are open, all Low. None changes the primary H1 detection or QLIKE computation; 12 concerns the H1 p-value (block bootstrap) and extends the disclosed remainder of audit 1 finding 4.", "",
     "| # | Severity | Finding | What it affects |", "|---|---|---|---|",
     "| 10 | Low | Student-t keeps the last attempt, not the best, when all 10 attempts of a start fail (`s5_models.py:198-209`) | Only fits that end flagged (A14.2); those are counted and excluded in the 5.10 sensitivity. |",
     "| 11 | Low | Greedy selection adds features when QLIKE is non-finite (`s5_select.py:37-38`) | Only a degenerate objective (all losses infinite). |",
     "| 12 | Low | Block bootstrap blocks can span LEGACY 26 -> RAW 0 (`s5_h1.py`) | H1 p-values (5.9); same class as audit 1 finding 4's remainder. |",
     "| 13 | Low | Flagged-fit counts and EM cap hits not in `run_summary.json` (`s5_run.py`) | Reporting (5.4); per-fold scores carry the flags. |",
     "| 14 | Low | Feature caches `{era}_features.npz`, `{era}_bases.npz` keyed by column name only (`s5_lib.py:112-116`, `s5_fast.py:16-23`) | A change of feature code or panel would reuse cached columns. |",
     "| 15 | Low | 5.16 says the backend reads no session outside a fold's segments; it reads the whole era panel for past-session baselines | Record accuracy only; no model is fitted outside the fold's inner train. |"]
(ROOT / "OPEN_AUDIT_FINDINGS.md").write_text("\n".join(O) + "\n", encoding="utf-8"); side("OPEN_AUDIT_FINDINGS.md")

# ---------- protocol
t = P.read_text(encoding="utf-8")
def rep(a, b):
    global t; assert t.count(a) == 1, a[:70]; t = t.replace(a, b)
rep("(integrated through Amendment A14.2)", "(integrated through Amendment A15)")
t = re.sub(r"Re-frozen with A14\.2 \S+ UTC \(\S+ New York; ", f"Re-frozen with A15 {now.isoformat()} UTC ({now.astimezone(ZoneInfo('America/New_York')).isoformat()} New York; ", t, count=1)
rep("and with A14 earlier on 2026-11-04)", "and with A14 earlier on 2026-11-04 and with A14.2 at 2026-11-04T00:29 UTC)")
rep("Amendments A6 to A14.2. ", "Amendments A6 to A15. ")
rep("through A14.1 as `SECTION5_PROTOCOL_v5_FROZEN_A14_1.md` (sha256 `51264c1d8bfb23fd446756308151a7cdaa9cc80b66f50f98a248dd14eb438fad`)", f"through A14.1 as `SECTION5_PROTOCOL_v5_FROZEN_A14_1.md` (sha256 `51264c1d8bfb23fd446756308151a7cdaa9cc80b66f50f98a248dd14eb438fad`), through A14.2 as `SECTION5_PROTOCOL_v6_FROZEN_A14_2.md` (sha256 `{sha(V6)}`)")
rep("\n\nSupporting records", "\n| A15 | `AMENDMENT_A15.md` | cold audit 2: baseline tuning, contamination guard, checkpoint versions, main-run path, Holm, H1(a) failures, freeze hashes, label-free statistics, reclassification | `%s` |\n\nSupporting records" % sha(ROOT / "AMENDMENT_A15.md"))
rep("Supporting records (not part of the rules): cold audit `section5_cold_audit.md`", "Supporting records (not part of the rules): cold audits `section5_cold_audit.md` and `section5_cold_audit_2.md`")
rep("baselines = the deseasonalized 5-min return only, same architecture and hyperparameter budget.", "baselines = the deseasonalized 5-min return only, same architecture and hyperparameter budget (A15 rule 1: the baseline's K/lambda is tuned on the fold's validation QLIKE with the identical grid, 3 starts and tie rule; the 5.13 final setups also carry the baseline parameters).")
rep("A fold with fewer than 8 stable test days skips H1(a), recorded, without error (A6 item 2, A8 item 3).", "A fold with fewer than 8 stable test days skips H1(a), recorded, without error (A6 item 2, A8 item 3); a fold with 8 or more whose splice construction fails is recorded as an H1(a) failure with its reason, not as a skip or a zero effect, and is listed in every report (A15 rule 6b).")
rep("5.11 Holm: H1 across the three H1 families (BOCPD excluded);", "5.11 Holm: H1 across the three H1 families (BOCPD excluded; a family p-value that cannot be evaluated enters as 1 and counts in m, A15 rule 6a);")
rep("5.12 Freeze final setups, thresholds (era-level, 5.13) and hashes before", "5.12 Freeze final setups (with the baseline parameters), thresholds (era-level, 5.13, computed only after every fold has been selected and scored; A15 rule 5c) and hashes (protocol, every integrated amendment, cited inputs, split manifest, contamination list, H1(c) times, LEGACY and RAW panel and SPY ETF files; A15 rule 6c) before")
rep("used it for a statistic that informed a protocol decision; embargo sessions included.", "used it for a statistic that informed a protocol decision; embargo sessions included. An analysis that runs no detector or regime model and uses no outcome (session or stable-day counts, bar validity shares, splice specifications, feature or preprocessing computation) does not touch a session (A15 rule 6d).")
rep("from a registry of every script that loads data (a unit test fails if one is missing)", "from a registry of every script that loads data, including the first cold audit's scripts (A15 rule 2); `check_registry` fails on an unregistered data-loading script and a unit test shows that it can (A15 rule 3)")
rep("Result at freeze: 6 of 34 folds excluded (LEGACY 27, 28, 29; RAW 1, 2, 3); 28 folds confirmatory.", "Result at freeze (regenerated under A15): 8 of 34 folds excluded (LEGACY 23, 24, 27, 28, 29; RAW 1, 2, 3); 26 folds confirmatory. `run_all` loads this list itself (A15 rule 5d).")
rep("106 eligible events remain in uncontaminated test segments", "98 eligible events remain in uncontaminated test segments (106 before A15)")
rep("Orchestration `section5/s5_run.py` with code-version-keyed checkpoints;", "Orchestration `section5/s5_run.py` with checkpoints keyed by the hash of every result-affecting module (import closure), the backend kind and the budget (A15 rule 4); main-run backend `s5_main.py` (A15 rule 5);")
rep("Machinery checks may use only the contaminated folds (RAW 3, LEGACY 29); the backend refuses any other fold and any session outside a fold's own segments.", "Machinery checks may use only the contaminated folds (RAW 3, LEGACY 29); the backend serves a clean fold only with the sha256 of the FROZEN protocol matching its sidecar (A15 rule 5b) and refuses any session outside a fold's own segments.")
a = t.index("- Cold audit findings (`COLD_AUDIT_STATUS.md`"); b = t.index("- The era-level calibration")
t = t[:a] + ("- Cold audit findings (`COLD_AUDIT_STATUS.md`, `OPEN_AUDIT_FINDINGS.md`). Audit 1: 8 open (10, 13, 17 Medium; 12, 16, 18, 20, 21 Low), 4 disclosed (1 residual, 2, 5, 8) and 4 resolved with a disclosed remainder, 10 resolved (3 and 11 reopened by audit 2 and resolved by A15). "
             "Audit 2: 9 resolved by A15, 6 open (10-15, Low). None of the open ones changes the primary detection or QLIKE computation; audit 2 finding 12 concerns the H1 block bootstrap across the era boundary.\n") + t[b:]
rep("- The era-level calibration (A11 item 1) is implemented and unit-tested for the split; it has not been run on data.", "- The era-level calibration (A11 item 1) is implemented and unit-tested for the split; it has not been run on data; it is reached only through `s5_main.MainBackend` after a complete run (A15). The main run (A15 rule 5) has not been run.")
P.write_text(t, encoding="utf-8"); side("SECTION5_PROTOCOL.md"); print("protocol", sha(P))
