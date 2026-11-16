#!/usr/bin/env python3
"""Paper figures (PDF + PNG, 300 dpi) from stored result files. READ-ONLY on research results: it reads written JSON/CSV
outputs and the development feature cache (TRAIN span only), never the evaluation panels, and writes only paper/figures/.
Runs under any Python with numpy + matplotlib (the research environment has no matplotlib; the figures were made with the
system Python 3.12 / matplotlib 3.11.2, which computes nothing that enters a result).

Figure-only statistics, labelled in the captions (paper/FIGURES.md) and not protocol results:
  fig1  development 95% intervals = percentile bootstrap of the fold mean over confirmatory folds (10,000 resamples, seed 0);
  fig2  95% Wilson intervals of the evaluation hit rates (the stored evaluation interval is for the paired difference only);
  fig6  per-slot medians of the development feature cache (descriptive).
Usage: python paper/make_figures.py"""
import json, hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent; OUT = ROOT / "paper" / "figures"; OUT.mkdir(parents=True, exist_ok=True)
R5 = ROOT / "section5" / "results"; R6 = ROOT / "section6" / "results"
L = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))
FAMS = ["gaussian_hmm", "student_t_hmm", "hsmm"]
NAME = {"gaussian_hmm": "Gaussian HMM", "student_t_hmm": "Student-t HMM", "hsmm": "HSMM"}
COL = {"gaussian_hmm": "#2a78d6", "student_t_hmm": "#eb6834", "hsmm": "#1baf7a"}          # dataviz reference palette, slots 1-3 (all-pairs validated)
MRK = {"gaussian_hmm": "o", "student_t_hmm": "s", "hsmm": "D"}
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
ASSETS = [("TLT", "TLT"), ("HYG", "HYG"), ("GOLD", "Gold"), ("DOLLAR", "USD")]

plt.rcParams.update({"font.family": "serif", "font.serif": ["DejaVu Serif"], "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5,
                     "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 7.5, "axes.edgecolor": AXIS, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": 0.5, "axes.axisbelow": True, "lines.linewidth": 1.5, "pdf.fonttype": 42, "savefig.dpi": 300})
SOURCES = {}; STATS = {}


def save(fig, name, sources):
    for ext in ("pdf", "png"): fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight", facecolor="white")
    plt.close(fig); SOURCES[name] = {str(Path(s).relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(Path(s).read_bytes()).hexdigest() for s in sources}


def zero(ax): ax.axhline(0, color=AXIS, lw=0.8, zorder=1)


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d; return c - h, c + h


# ---------- MR2 per-fold scores (development)
def mr2_scores():
    rec = L(R5 / "main_run_2" / "run_complete.json"); out = {}
    for p in (R5 / "main_run_2" / "ckpt").glob("*.json"):
        c = L(p); k = c["key"].split("|")
        if c["version"] != rec["checkpoint_version"]: raise SystemExit("MR2 checkpoint version mismatch")
        if k[0] == "score": out[(f"{k[3]}|{k[4]}", k[5])] = c["value"]
    assert len(out) == 136, len(out); return out


def fig1():
    summ = L(R5 / "main_run_2" / "run_summary.json"); excl = set(summ["excluded"]); sc = mr2_scores(); rng = np.random.default_rng(0)
    ev = {e: L(R5 / f"evaluation_{e}.json")["families"] for e in ("LEGACY", "RAW")}
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0), gridspec_kw=dict(width_ratios=[1.15, 1]), sharey=True)
    ax = axes[0]
    for i, fam in enumerate(FAMS):
        a = np.array([sc[(f, fam)]["a"] for f in summ["folds"] if f not in excl and sc[(f, fam)]["a"] is not None and not sc[(f, fam)].get("a_skipped")], float)
        assert len(a) == summ["family_results"][fam]["confirmatory"]["H1a"]["n_folds"] and np.isclose(a.mean(), summ["family_results"][fam]["confirmatory"]["H1a"]["mean"])
        bm = rng.choice(a, (10000, len(a))).mean(1); lo, hi = np.percentile(bm, [2.5, 97.5]); STATS.setdefault("fig1_dev_fold_bootstrap_95", {})[fam] = dict(n_folds=len(a), mean=float(a.mean()), lo=float(lo), hi=float(hi), n_negative=int((a < 0).sum()), n_zero=int((a == 0).sum()))
        x = i + (rng.random(len(a)) - 0.5) * 0.28
        ax.scatter(x, a, s=10, color=COL[fam], alpha=0.35, lw=0, zorder=2)
        ax.errorbar(i, a.mean(), yerr=[[a.mean() - lo], [hi - a.mean()]], fmt=MRK[fam], color=COL[fam], ms=6, mec="white", mew=0.8, capsize=3, lw=1.5, zorder=3)
        ax.annotate(f"{a.mean():+.3f}", (i + 0.2, a.mean()), color=INK, fontsize=7.5, va="center")
    zero(ax); ax.set_xticks(range(3), ["Gaussian\nHMM", "Student-t\nHMM", "HSMM"]); ax.set_xlim(-0.5, 2.7)
    ax.set_ylabel("H1(a) pAUC gain (feature − returns-only)"); ax.set_title("(a) Development: 22 confirmatory folds", loc="left")
    ax = axes[1]; off = {"LEGACY": -0.15, "RAW": 0.15}; mk = {"LEGACY": "o", "RAW": "^"}
    for i, fam in enumerate(FAMS):
        for e in ("LEGACY", "RAW"):
            h = ev[e][fam]["H1a"]; y = h["effect"]; lo, hi = h["ci95"]
            ax.errorbar(i + off[e], y, yerr=[[y - lo], [hi - y]], fmt=mk[e], color=COL[fam], mfc=COL[fam] if e == "RAW" else "white", ms=6, mew=1.2, capsize=3, lw=1.5)
            ax.annotate(f"{y:+.3f}", (i + off[e] + 0.07, y), color=INK, fontsize=7, va="center")
    zero(ax); ax.set_xticks(range(3), ["Gaussian\nHMM", "Student-t\nHMM", "HSMM"]); ax.set_xlim(-0.5, 2.7)
    ax.set_title("(b) Evaluation (frozen models)", loc="left")
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], marker="o", ls="", color=INK2, mfc="white", label="LEGACY 2019–22 (79 stable days)"),
                       Line2D([], [], marker="^", ls="", color=INK2, label="RAW 2025–26 (115 stable days)")], loc="upper left", frameon=False)
    save(fig, "fig1_h1a_pauc_gain", [R5 / "main_run_2" / "run_summary.json", R5 / "main_run_2" / "run_complete.json", R5 / "evaluation_LEGACY.json", R5 / "evaluation_RAW.json"])


def fig2():
    a17 = L(R5 / "mr2" / "a17" / "a17_results.json")["h1c"]; ev = {e: L(R5 / f"evaluation_{e}.json")["families"] for e in ("LEGACY", "RAW")}
    panels = [("(a) Development (98 events)", {f: (a17[f]["f3"]["hit_rate"], a17[f]["f3"]["wilson95"], a17[f]["base"]["hit_rate"], a17[f]["base"]["wilson95"]) for f in FAMS})]
    for e, lab in (("LEGACY", "(b) Eval. LEGACY (24 events)"), ("RAW", "(c) Eval. RAW (14 events)")):
        d = {}
        for f in FAMS:
            h = ev[e][f]["H1c"]; n = h["n_events"]; k1, k0 = round(h["mean1"] * n), round(h["mean0"] * n); d[f] = (h["mean1"], wilson(k1, n), h["mean0"], wilson(k0, n)); STATS.setdefault("fig2_eval_wilson_95", {})[f"{e}|{f}"] = dict(n=n, feature=[k1, *map(float, wilson(k1, n))], baseline=[k0, *map(float, wilson(k0, n))])
        panels.append((lab, d))
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.7), sharey=True)
    for ax, (title, d) in zip(axes, panels):
        for i, f in enumerate(FAMS):
            p1, c1, p0, c0 = d[f]
            ax.errorbar(i - 0.13, p1, yerr=[[p1 - c1[0]], [c1[1] - p1]], fmt=MRK[f], color=COL[f], ms=5.5, mec="white", mew=0.7, capsize=2.5, lw=1.3)
            ax.errorbar(i + 0.13, p0, yerr=[[p0 - c0[0]], [c0[1] - p0]], fmt=MRK[f], color=MUTED, mfc="white", ms=5.5, mew=1.1, capsize=2.5, lw=1.3)
        ax.set_xticks(range(3), ["Gaussian\nHMM", "Student-t\nHMM", "HSMM"]); ax.set_ylim(0, 1); ax.set_xlim(-0.5, 2.5); ax.set_title(title, loc="left", fontsize=8.5)
    axes[0].set_ylabel("Hit rate in [release, release + 60 min]")
    from matplotlib.lines import Line2D
    axes[0].legend(handles=[Line2D([], [], marker="o", ls="", color=INK2, label="feature model (filled, family colour)"),
                            Line2D([], [], marker="o", ls="", color=MUTED, mfc="white", label="returns-only baseline (open, grey)")], loc="upper center", ncol=2, frameon=False, bbox_to_anchor=(1.65, -0.3))
    save(fig, "fig2_fomc_hit_rates", [R5 / "mr2" / "a17" / "a17_results.json", R5 / "evaluation_LEGACY.json", R5 / "evaluation_RAW.json"])


def fig3():
    d = L(R5 / "posthoc_absolute_detection.json")["development"]["LEGACY"]["confirmatory"]; ratios = ["1.5", "2", "3", "5", "10"]; xs = np.array([1.5, 2, 3, 5, 10])
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 2.7), gridspec_kw=dict(wspace=0.38))
    for j, direc in enumerate(("up", "down")):
        ax = axes[j]
        for f in FAMS:
            for m, ls, mf in (("feature", "-", COL[f]), ("baseline", "--", "white")):
                y = [d[f][m]["by_ratio_direction"][f"R{r}|{direc}"]["hit60_rate"] for r in ratios]
                ax.plot(xs, y, ls=ls, color=COL[f], marker=MRK[f], ms=4.5, mfc=mf, mew=1, lw=1.4 if m == "feature" else 1.0, label=f"{NAME[f]}, {m}")
        ax.set_xscale("log"); ax.set_xticks(xs, ["1.5", "2", "3", "5", "10"]); ax.minorticks_off(); ax.set_ylim(0, 0.8)
        ax.set_xlabel("Planted variance ratio"); ax.set_title(f"({'ab'[j]}) Hit within 60 min, {direc}", loc="left", fontsize=8.5)
    axes[0].set_ylabel("Share of break splices hit")
    ax = axes[2]
    for k, f in enumerate(FAMS):
        q = [d[f]["feature"]["by_ratio_direction"][f"R{r}|up"]["delay60_min"] for r in ratios]
        med = np.array([v["median"] for v in q]); lo = med - np.array([v["q25"] for v in q]); hi = np.array([v["q75"] for v in q]) - med
        ax.errorbar(xs * (1 + (k - 1) * 0.06), med, yerr=[lo, hi], fmt=MRK[f] + "-", color=COL[f], ms=4.5, mec="white", mew=0.6, capsize=2, lw=1.3)
    ax.set_xscale("log"); ax.set_xticks(xs, ["1.5", "2", "3", "5", "10"]); ax.minorticks_off(); ax.set_ylim(0, 60)
    ax.set_xlabel("Planted variance ratio"); ax.set_ylabel("Onset to confirmation (min)"); ax.set_title("(c) Delay of hits, up", loc="left", fontsize=8.5)
    h, l = axes[0].get_legend_handles_labels(); fig.legend(h, l, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.24))
    save(fig, "fig3_detection_by_break_size", [R5 / "posthoc_absolute_detection.json"])


def fig4():
    dev = {f: L(R6 / f"s6_development_{f}.json")["primary"] for f in ("gaussian_hmm", "hsmm")}; ev = L(R6 / "s6_evaluation_gaussian_hmm.json")["primary"]
    ci = L(R6 / "posthoc" / "h3_ci_a29_3b.json")["by_detector"]
    rows = [("Development, Gaussian HMM", "gaussian_hmm", dev["gaussian_hmm"], ci["gaussian_hmm"], "o", COL["gaussian_hmm"], True),
            ("Development, HSMM", "hsmm", dev["hsmm"], ci["hsmm"], "D", COL["hsmm"], True),
            ("Evaluation, Gaussian HMM", "gaussian_hmm", ev, {}, "^", COL["gaussian_hmm"], False)]
    fig, ax = plt.subplots(figsize=(6.2, 2.9)); off = [-0.22, 0.0, 0.22]
    for r, (lab, fam, prim, cis, mk, c, filled) in enumerate(rows):
        for i, (key, an) in enumerate(ASSETS):
            p = prim[f"H3_{key}"]; g = p["gamma"]; x = i + off[r]; n = p["n_breaks"]
            if key in cis:
                lo, hi = cis[key]["ci95"]; ax.errorbar(x, g, yerr=[[g - lo], [hi - g]], fmt=mk, color=c, mfc=c if filled else "white", ms=6, mew=1.2, capsize=3, lw=1.5)
            else:
                ax.plot(x, g, mk, color=c, mfc="white" if not filled else c, ms=6, mew=1.2, alpha=1 if not filled else 0.55)
        ax.plot([], [], mk, color=c, mfc=c if filled else "white", ms=6, label=lab)
    zero(ax); ax.set_xticks(range(4), [a for _, a in ASSETS]); ax.set_ylim(-0.33, 0.06); ax.set_xlim(-0.5, 3.5)
    ax.set_ylabel(r"H3 break coefficient $\gamma$ (log next-day RV)")
    ax.legend(loc="upper right", frameon=False, ncol=1)
    ax.set_title("H3 next-day volatility response (one-sided H0: γ ≤ 0; no test rejects)", loc="left")
    save(fig, "fig4_h3_gamma", [R6 / "s6_development_gaussian_hmm.json", R6 / "s6_development_hsmm.json", R6 / "s6_evaluation_gaussian_hmm.json", R6 / "posthoc" / "h3_ci_a29_3b.json"])


def fig5():
    dev = L(R6 / "s6_development_gaussian_hmm.json")["a30_lead_lag"]; ev = L(R6 / "s6_evaluation_gaussian_hmm.json")["a30_lead_lag"]
    fig, axes = plt.subplots(1, 4, figsize=(7.4, 2.4), sharey=True)
    bins = np.arange(-30, 125, 5)
    for ax, (key, an) in zip(axes, ASSETS):
        for src, lab, c, a in ((dev, "Development", "#2a78d6", 0.9), (ev, "Evaluation", "#eb6834", 0.9)):
            v = src["breaks"]["all"]["by_asset"].get(key)
            if not v or not v.get("counts_rel_S"): continue
            cnt = {int(k): n for k, n in v["counts_rel_S"].items()}; tot = sum(cnt.values()); y = np.array([cnt.get(int(b), 0) / tot for b in bins])
            ax.step(bins, y, where="mid", color=c, lw=1.4, alpha=a, label=f"{lab} (n={tot})")
        ax.axvline(0, color=INK2, lw=0.8, ls=":"); ax.set_title(an, loc="left"); ax.legend(frameon=False, fontsize=6.5, loc="upper right")
        ax.set_xlim(-32, 122)
    axes[0].set_ylabel("Share of first exceedances"); fig.supxlabel("Minutes from S (first update of the confirming SPY run); 5-min bars", fontsize=8.5)
    fig.suptitle("A30: first 5-min bar where the asset's |cumulative return| exceeds its placebo 90th percentile (Gaussian HMM breaks)", x=0.01, ha="left", fontsize=8.5)
    fig.tight_layout()
    save(fig, "fig5_a30_timing", [R6 / "s6_development_gaussian_hmm.json", R6 / "s6_evaluation_gaussian_hmm.json"])


def fig6():
    cache = ROOT / "section5" / "cache"; bars = L(R5 / "session_bars.json"); pairs = [("abs_return_1m", "|1-min return|"), ("rv10_partial90", "rv10_partial90")]
    fig, axes = plt.subplots(2, 2, figsize=(7.0, 4.4), sharex=True); srcs = [R5 / "session_bars.json"]
    for j, era in enumerate(("LEGACY", "RAW")):
        z = np.load(cache / f"{era}_features.npz"); b = np.array(bars[era]); assert b.sum() == len(z["return_1m"])
        starts = np.r_[0, np.cumsum(b)[:-1]]; full = starts[b == 390]; idx = full[:, None] + np.arange(390)[None, :]; srcs.append(cache / f"{era}_features.npz")
        for i, (col, lab) in enumerate(pairs):
            ax = axes[i, j]
            for c, name, colr, ls in ((col, "raw feature", MUTED, "-"), (col + "__sadj", "seasonally adjusted (__sadj)", "#2a78d6", "-")):
                M = z[c][idx]; med = np.nanmedian(M, axis=0); med = med / np.nanmedian(med)
                ax.plot(np.arange(390), med, color=colr, lw=1.3, ls=ls, label=name)
            ax.axhline(1, color=AXIS, lw=0.8)
            ax.set_title(f"({'abcd'[2 * i + j]}) {era} TRAIN, {lab}", loc="left", fontsize=8.5)
            ax.set_xticks([0, 90, 180, 270, 360], ["9:30", "11:00", "12:30", "14:00", "15:30"])
        axes[1, j].set_xlabel("Minute of the session (ET)")
    fig.supylabel("Median by minute ÷ median over minutes", fontsize=8.5)
    axes[0, 0].legend(frameon=False, loc="upper right")
    fig.tight_layout()
    save(fig, "fig6_seasonality", srcs)


if __name__ == "__main__":
    for fn in (fig1, fig2, fig3, fig4, fig5, fig6): fn(); print("done", fn.__name__)
    (OUT / "figure_sources.json").write_text(json.dumps(SOURCES, indent=1), encoding="utf-8"); (OUT / "figure_stats.json").write_text(json.dumps(STATS, indent=1), encoding="utf-8")
