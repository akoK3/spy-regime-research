#!/usr/bin/env python3
"""Step 4: measure lookback, minimum valid observations and warmup of all 81 outputs from the
code itself (by perturbing a fully valid synthetic panel), then compare with the frozen protocol.

Probes (probe row = last session, slot 65 of 72):
  A  bump one earlier bar of the probe session (x0.2 and x5)      -> lookback in bars
  B  bump a whole earlier session                                  -> sessions of history
  C  blank returns back from the probe row                         -> tolerated missing returns
  D  blank one bar at a time                                       -> bars that are individually required
  E  blank the same-slot bar of earlier sessions, newest first     -> tolerated missing sessions
  F  bump bars after the probe row                                 -> must change nothing (no lookahead)
Warmup is the first finite session and slot on the unperturbed panel.
No feature formula is changed; this only reads the existing generators.
"""
import sys, json, hashlib, re, math, warnings, datetime, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import step3_all_in_one as s  # noqa: E402

warnings.simplefilter("ignore")
OUT = s.OUT
PROTOCOL = Path(r"C:\Users\kakij\OneDrive\Desktop\data\section4_3_rebuild_20261028\protocol_20261029T032641Z.json")
PROTOCOL_SHA = "3d6f0c96fce1c05f8e94d1a8c6e6b14a5b5b1c9f013e6a95dd1e96498cbfff8b"
SESS, LEN, T_SESS, T_SLOT = 24, 72, 23, 65
P = T_SESS * LEN + T_SLOT
FACTORS = (0.2, 5.0)
CHANNELS = ("close", "open", "high", "low", "volume")
START = time.time()


def log(msg):
    print(f"[{(time.time()-START)/60:6.1f} min] {msg}", flush=True)


def base_bars():
    rng = np.random.default_rng(43104)
    n = SESS * LEN
    steps = rng.standard_normal(n) * 5e-4
    logp = np.empty(n)
    for k in range(SESS):
        a = k * LEN
        logp[a:a+LEN] = np.log(100) + rng.normal(0, .01) + np.cumsum(steps[a:a+LEN])
    close = np.exp(logp)
    close[P] *= 1.05  # large move on the probe row so the Lee-Mykland flag is 1
    volume = rng.lognormal(7, .4, size=n)
    up, dn = np.abs(rng.normal(0, 4e-4, n)) + 1e-5, np.abs(rng.normal(0, 4e-4, n)) + 1e-5
    return dict(close=close, volume=volume, high=close*np.exp(up), low=close*np.exp(-dn),
                open=close*np.exp(rng.normal(0, 3e-4, n)))


def build(bars):
    n = SESS * LEN
    slot = np.tile(np.arange(LEN), SESS)
    c = bars["close"]
    prev = np.r_[np.nan, c[:-1]]
    valid = (slot > 0) & np.isfinite(c) & np.isfinite(prev)
    r = np.full(n, np.nan); r[valid] = np.log(c[valid] / prev[valid])
    first = np.arange(0, n, LEN)
    t = np.arange(n, dtype=np.int64) * 60_000_000_000
    return dict(era="PROBE", t=t, available=t + 60_000_000_000, day=np.repeat([f"2022-04-{k+1:02d}" for k in range(SESS)], LEN),
                slot=slot, r=r, valid=valid, close=c.copy(), range=np.log(bars["high"] / bars["low"]),
                volume=bars["volume"].copy(), first=first, end=first + LEN,
                open=bars["open"].copy(), high=bars["high"].copy(), low=bars["low"].copy())


def compute(d):
    return {**s.construct(d)[0], **s.construct_additions(d), **s.construct_deferred(d)}


def row(bars, mutate=None):
    d = build(bars)
    if mutate: mutate(d)
    return {k: float(v[P]) for k, v in compute(d).items()}


def copy_bars(bars):
    return {k: v.copy() for k, v in bars.items()}


def changed(a, b):
    if np.isnan(a) and np.isnan(b): return False
    if np.isnan(a) != np.isnan(b): return True
    # Cumulative-sum features carry ~1e-13 absolute floating-point noise from earlier bars; real influence is >1e-3 relative.
    return not np.isclose(a, b, rtol=1e-6, atol=0)


def bump(bars, index_or_slice, f):
    for ch in CHANNELS: bars[ch][index_or_slice] *= f


def blank(bars, idx):
    for ch in CHANNELS: bars[ch][idx] = np.nan


def frozen_spec(name):
    """Expected parameters from the frozen protocol definitions (see check_protocol for the quoted text)."""
    if name in ("return_1m", "abs_return_1m"):
        return dict(L=1, kind="ret", min=1, slot=1, sess=0, S=0)
    if name in ("intrabar_range_log", "raw_volume", "log_raw_volume"):
        return dict(L=0, kind="bar", min=1, slot=0, sess=0, S=0)
    if name in ("relative_volume20", "log_relative_volume20"):
        return dict(L=0, kind="sess", min=10, slot=0, sess=10, S=20)
    if name == "rv60_sampled5_exact":
        return dict(L=60, kind="bar", min=13, slot=60, sess=0, S=0)
    if name == "shock_prior60_mad":
        return dict(L=61, kind="ret", min=61, slot=61, sess=0, S=0)
    m = re.fullmatch(r"(rv|downside|momentum)(\d+)_(strict|partial90|endpoint)", name)
    if m:
        w, kind = int(m.group(2)), m.group(3)
        if kind == "strict": return dict(L=w, kind="ret", min=w, slot=w, sess=0, S=0)
        if kind == "partial90": return dict(L=w, kind="ret", min=math.ceil(.9 * w), slot=w, sess=0, S=0)
        return dict(L=w, kind="bar", min=2, slot=w, sess=0, S=0)
    return None


FORBIDDEN = {"overnight_return_open": "frozen clocks.overnight: 'No overnight returns; first-minute return absent every session'"}


def check_protocol():
    raw = PROTOCOL.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PROTOCOL_SHA, "frozen protocol hash changed"
    p = json.loads(raw.decode("utf-8"))
    df = p["definitions"]
    quotes = [("partial90", "n>=ceil(.90 W)"), ("partial90", "full W-minute clock window"), ("strict", "slot>=W"),
              ("volume", "previous 20 scheduled sessions, at least 10 positives"), ("shock", "require 61 consecutive eligible returns including current"),
              ("sampled5", "closes at t,t-5,...,t-60"), ("endpoint_momentum", "exact two closes and same session"), ("return_1m", "within-session closes")]
    for key, text in quotes: assert text in df[key], f"protocol text changed: {key}: {text}"
    assert "No overnight returns" in p["clocks"]["overnight"]
    assert p["windows_minutes"] == [5, 10, 15, 30, 60]
    return p


def main():
    protocol = check_protocol()
    bars = base_bars()
    d0 = build(bars)
    base_full = compute(d0)
    names = list(base_full)
    assert len(names) == s.EXPECTED_ORIGINAL + s.EXPECTED_ADDITIONAL == 81, len(names)
    base = {k: float(v[P]) for k, v in base_full.items()}
    unusable = [k for k, v in base.items() if np.isnan(v)]
    assert not unusable, f"probe row not finite for {unusable}"
    log(f"base panel computed, {len(names)} outputs, probe row finite for all")

    # warmup
    warm = {}
    for k, v in base_full.items():
        v = np.asarray(v, float).reshape(SESS, LEN)
        sessions = np.flatnonzero(np.isfinite(v).any(axis=1))
        last = np.flatnonzero(np.isfinite(v[T_SESS]))
        warm[k] = (int(sessions[0]) if len(sessions) else None, int(last[0]) if len(last) else None)

    # A: lookback inside the probe session
    lookback = {k: 0 for k in names}
    for k in range(1, T_SLOT + 1):
        for f in FACTORS:
            b = copy_bars(bars); bump(b, P - k, f)
            r = row(b)
            for name in names:
                if changed(base[name], r[name]): lookback[name] = max(lookback[name], k)
        if k % 15 == 0: log(f"A lookback k={k}/{T_SLOT}")

    # B: sessions of history
    sess_back = {k: 0 for k in names}
    for m in range(1, T_SESS + 1):
        for f in FACTORS:
            b = copy_bars(bars); bump(b, slice((T_SESS - m) * LEN, (T_SESS - m + 1) * LEN), f)
            r = row(b)
            for name in names:
                if changed(base[name], r[name]): sess_back[name] = max(sess_back[name], m)
    log("B sessions of history done")

    # C: blank returns
    first_nan_r = {k: None for k in names}  # smallest m such that blanking the m newest returns (t-m+1..t) makes the output NaN
    def kill(idx):
        def mut(d): d["r"][idx] = np.nan; d["valid"][idx] = False
        return mut
    for m in range(1, T_SLOT + 1):
        r = row(bars, kill(slice(P - m + 1, P + 1)))
        for name in names:
            if first_nan_r[name] is None and np.isnan(r[name]): first_nan_r[name] = m
    log("C return removal done")

    # D: single required bars
    required = {k: [] for k in names}
    positions = list(range(P - T_SLOT, P + 1)) + [T_SESS * LEN - 1]
    for p in positions:
        b = copy_bars(bars); blank(b, p)
        r = row(b)
        for name in names:
            if np.isnan(r[name]): required[name].append(p)
    log("D single-bar knockouts done")

    # E: same-slot bars of earlier sessions, newest first
    first_nan_s = {k: None for k in names}
    for m in range(1, T_SESS + 1):
        b = copy_bars(bars)
        for j in range(1, m + 1): blank(b, (T_SESS - j) * LEN + T_SLOT)
        r = row(b)
        for name in names:
            if first_nan_s[name] is None and np.isnan(r[name]): first_nan_s[name] = m
    log("E session removal done")

    # F: bars after the probe row
    uses_future = {k: False for k in names}
    for j in range(1, LEN - T_SLOT):
        for f in FACTORS:
            b = copy_bars(bars); bump(b, P + j, f)
            r = row(b)
            for name in names:
                if changed(base[name], r[name]): uses_future[name] = True
    log("F future-bar check done")

    table = []
    for name in names:
        # A bar that only decides whether the output exists (not its value) still belongs to the lookback.
        in_session = [P - p for p in required[name] if T_SESS * LEN <= p < P]
        if in_session: lookback[name] = max(lookback[name], max(in_session))
        L, S = lookback[name], sess_back[name]
        if first_nan_r[name] is not None:
            kind = "ret"; mn = max(1, L - (first_nan_r[name] - 1))
        elif first_nan_s[name] is not None and S > 0:
            kind = "sess"; mn = S - (first_nan_s[name] - 1)
        else:
            kind = "bar"; mn = len(required[name])
        got = dict(L=L, kind=kind, min=mn, slot=warm[name][1], sess=warm[name][0], S=S)
        spec = frozen_spec(name)
        problems = []
        if uses_future[name]: problems.append("uses bars after t (lookahead)")
        if name in FORBIDDEN: problems.append(FORBIDDEN[name])
        if spec is None:
            status = "FAIL" if problems else "NO_SPEC"
        else:
            for key in ("L", "kind", "min", "slot", "sess", "S"):
                if got[key] != spec[key]: problems.append(f"{key}: code {got[key]} vs frozen {spec[key]}")
            status = "FAIL" if problems else "PASS"
        table.append(dict(output=name, group="original" if name in s.construct(d0)[0] else "added", extracted=got, frozen=spec, status=status, problems=problems))

    listed = set(protocol["candidate_features"])
    in_code = {r["output"] for r in table if r["group"] == "original"}
    assert listed == in_code, (sorted(listed ^ in_code))
    result = dict(generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), frozen_protocol=PROTOCOL.name,
                  frozen_protocol_sha256=PROTOCOL_SHA, probe=dict(sessions=SESS, session_length=LEN, probe_session=T_SESS, probe_slot=T_SLOT),
                  counts={k: sum(r["status"] == k for r in table) for k in ("PASS", "FAIL", "NO_SPEC")}, rows=table)
    (OUT / "step4_parameter_table.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    def fmt_min(g):
        unit = {"ret": "returns", "bar": "bars", "sess": "sessions"}[g["kind"]]
        return f"{g['min']} {unit}"
    lines = ["| # | Output | Lookback (bars / sessions) | Min valid obs | Warmup (first slot / session) | Frozen amendment | Status |", "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(table, 1):
        g, f = r["extracted"], r["frozen"]
        frozen = "not specified" if f is None else f"{f['L']} / {f['S']}; {fmt_min(f)}; slot {f['slot']} / session {f['sess']}"
        note = "" if not r["problems"] else " — " + "; ".join(r["problems"])
        lines.append(f"| {i} | {r['output']} | {g['L']} / {g['S']} | {fmt_min(g)} | slot {g['slot']} / session {g['sess']} | {frozen} | {r['status']}{note} |")
    (OUT / "step4_parameter_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("\ncounts:", result["counts"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
