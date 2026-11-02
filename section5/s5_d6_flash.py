"""D6 supplement: the Flash Crash windows have 47 and 49 finite bars of 60 after T (panel gaps), below the pre-set 50 rule, so the main run reports NaN. Here the minimum is lowered to 40 for these two
windows ONLY (and for the 1,000 random moments, same rule), labelled as a deviation."""
import sys, json; sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import numpy as np, s5_lib as L, s5_d2_stable as S
d = L.load_era("LEGACY", L.pools()[0][:1]); dv = S.des_variance(d); days = np.array([str(d["day"][i]) for i in d["first"]]); n = len(days)
full = np.array([(d["end"][i] - d["first"][i]) == 390 for i in range(n)]); f = set(json.load(open(L.HERE / "results" / "d6_fomc_dates.json"))["scheduled_meetings_with_statement"].values().__iter__().__next__()) if False else set()
allf = {x for v in json.load(open(L.HERE / "results" / "d6_fomc_dates.json"))["scheduled_meetings_with_statement"].values() for x in v}
pool = np.array([i for i in range(21, n) if full[i] and days[i] not in allf and days[i] != "2010-05-06" and days[i] < "2019"]); rng = np.random.default_rng(6002)
def ratio(a, T, m=40):
    x, y = dv[a + T:a + T + 60], dv[a + T - 60:a + T]
    return float(np.nanmean(x) / np.nanmean(y)) if np.isfinite(x).sum() >= m and np.isfinite(y).sum() >= m else np.nan
i0 = int(np.where(days == "2010-05-06")[0][0]); out = []
for lab, T in (("14:32", 302), ("14:45", 315)):
    r = ratio(int(d["first"][i0]), T); rr = np.array([ratio(int(d["first"][i]), T) for i in rng.choice(pool, 1000)]); rr = rr[np.isfinite(rr)]
    out.append(dict(time=lab, ratio=r, percentile_among_random=float((rr < r).mean() * 100), random_median=float(np.median(rr)), random_q95=float(np.quantile(rr, .95)), n_random=len(rr)))
print(out); json.dump(out, open(L.HERE / "results" / "d6_flash_supplement.json", "w"), indent=1)
