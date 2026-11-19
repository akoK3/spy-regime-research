#!/usr/bin/env python3
"""Section 3.5: read-only Dukascopy quote-quality and freshness audit.

Run in PowerShell: python "$HOME/Downloads/section3_5_quote_quality.py"
Requires: python -m pip install numpy pandas pandas_market_calendars

The minute-close midpoint is an asynchronous, indicative quote proxy, NOT a
traded/executable price or evidence of actual tick freshness.

No ffill, no interpolation, no automatic deletion of suspect flat bars or
market-stress prices. Strictly past-facing flags versus retrospective case
summaries are identified separately. Source CSVs never modified.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

HOME = Path.home()
RAW = HOME / 'OneDrive' / 'Desktop' / 'data' / 'raw'
OUTPUT = HOME / 'Downloads' / 'section3_5_quote_quality_results'
MIN_NS = 60_000_000_000
CHUNK = 350_000

SOURCES = {
    'GOLD': {
        'bid': RAW / 'xauusd-m1-bid-2007-04-11-2026-10-02 - Copy.csv',
        'ask': RAW / 'xauusd-m1-ask-2007-04-11-2026-10-02.csv',
        'begin': '2007-04-11', 'end': '2026-10-01', 'jump_bp': 100.0,
    },
    'DOLLAR': {
        'bid': RAW / 'dollaridxusd-m1-bid-2017-12-01-2026-10-02.csv',
        'ask': RAW / 'dollaridxusd-m1-ask-2017-12-01-2026-10-02.csv',
        'begin': '2017-12-01', 'end': '2026-10-01', 'jump_bp': 50.0,
    },
}

EXPECTED_3_3 = {
    'GOLD': {'paired': 1_888_604, 'bid_only': 14_040, 'ask_only': 1_170,
             'neither': 16, 'spread_over_50': 38, 'joint_age_ge15': 350},
    'DOLLAR': {'paired': 788_472, 'bid_only': 57_750, 'ask_only': 14_820,
               'neither': 1_128, 'spread_over_50': 73, 'joint_age_ge15': 1_606},
}


def iso(ns: int) -> str:
    return pd.Timestamp(int(ns), unit='ns', tz='UTC').isoformat().replace('+00:00', 'Z')


def rth_grid(begin: str, end: str):
    try:
        import pandas_market_calendars as calendars
        sch = calendars.get_calendar('XNYS').schedule(start_date=begin, end_date=end)
    except ImportError:
        try:
            import exchange_calendars as calendars
            sch = calendars.get_calendar('XNYS',start=begin,end=end).schedule.rename(
                columns={'open':'market_open','close':'market_close'})
        except ImportError as exc:
            raise SystemExit('Install dependency: python -m pip install pandas_market_calendars') from exc
    opening = pd.DatetimeIndex(sch['market_open']).asi8
    closing = pd.DatetimeIndex(sch['market_close']).asi8
    grid = np.concatenate([np.arange(start, stop, MIN_NS, dtype=np.int64)
                           for start, stop in zip(opening, closing)])
    session = np.searchsorted(opening, grid, side='right') - 1
    assert np.all(grid < closing[session])
    return grid, session, sch


def locate(stamp, grid):
    p = np.searchsorted(grid, stamp)
    inside = p < len(grid)
    hit = inside & (grid[np.minimum(p, len(grid)-1)] == stamp)
    return p[hit], hit


def read_side(file: Path, grid):
    """Retain only NYSE RTH candle labels; others remain in original CSV."""
    if not file.is_file():
        raise FileNotFoundError(f'Missing source: {file}')
    n = len(grid)
    result = {key: np.full(n, np.nan, dtype=np.float64)
              for key in ('open', 'high', 'low', 'close')}
    result['present'] = np.zeros(n, dtype=bool)
    result['valid'] = np.zeros(n, dtype=bool)
    total = outside = 0
    for chunk in pd.read_csv(file, usecols=['timestamp','open','high','low','close'],
                             chunksize=CHUNK):
        total += len(chunk)
        ms = pd.to_numeric(chunk['timestamp'], errors='coerce')
        if ms.isna().any() or (ms < 100_000_000_000).any() or (ms > 100_000_000_000_000).any() or (ms % 60_000 != 0).any():
            raise ValueError(f'{file.name}: invalid or non-minute Unix-ms timestamp')
        ns = ms.astype(np.int64).to_numpy() * 1_000_000
        idx, hit = locate(ns, grid)
        outside += int((~hit).sum())
        if not len(idx):
            continue
        if result['present'][idx].any() or len(np.unique(idx)) != len(idx):
            raise ValueError(f'{file.name}: duplicate minute labels')
        values = chunk[['open', 'high', 'low', 'close']].to_numpy(dtype=np.float64)[hit]
        o, h, l, c = values.T
        valid = (np.isfinite(values).all(axis=1) & (values > 0).all(axis=1)
                 & (h >= np.maximum(o, c)) & (l <= np.minimum(o, c))
                 & (h >= l))
        result['present'][idx] = True
        result['valid'][idx] = valid
        for key, column in zip(('open', 'high', 'low', 'close'), values.T):
            result[key][idx] = column
    result['meta'] = {'source': str(file), 'total': total,
                      'in_rth': int(result['present'].sum()),
                      'outside_rth_or_period': outside,
                      'invalid_rth_ohlc': int((result['present'] & ~result['valid']).sum())}
    return result


def flat_age(flat, close, grid, sid, other_close=None):
    """Uninterrupted flat OHLC minute streak, *observable up to current minute*.

    A gap, session change, or price change resets age. Returns 0 if not flat.
    Vectorized for millions of observations; never uses future rows to mark t.
    """
    n = len(flat)
    if n == 0:
        return np.array([], dtype=np.int32)
    continuing = np.zeros(n, dtype=bool)
    continuing[1:] = (flat[1:] & flat[:-1]
                       & (grid[1:] - grid[:-1] == MIN_NS)
                       & (sid[1:] == sid[:-1])
                       & (close[1:] == close[:-1]))
    if other_close is not None:
        continuing[1:] &= (other_close[1:] == other_close[:-1])
    at = np.arange(n, dtype=np.int64)
    reset = np.maximum.accumulate(np.where(~continuing, at, 0))
    return np.where(flat, at - reset + 1, 0).astype(np.int32)


def compute_quality(grid, sid, bid, ask, jump_bp):
    n = len(grid)
    paired = bid['present'] & ask['present']
    healthy = paired & bid['valid'] & ask['valid']
    midpoint = np.full(n, np.nan)
    midpoint[healthy] = (bid['close'][healthy] + ask['close'][healthy]) / 2
    spread = np.full(n, np.nan)
    spread[healthy] = (10_000 * (ask['close'][healthy]-bid['close'][healthy])
                       / midpoint[healthy])
    crossed = healthy & (spread < 0)
    base = healthy & ~crossed

    bf = bid['valid'] & (bid['open'] == bid['high']) & (bid['high'] == bid['low']) & (bid['low'] == bid['close'])
    af = ask['valid'] & (ask['open'] == ask['high']) & (ask['high'] == ask['low']) & (ask['low'] == ask['close'])
    b_age = flat_age(bf, bid['close'], grid, sid)
    a_age = flat_age(af, ask['close'], grid, sid)
    joint_flat = bf & af & healthy
    # Pair jointly unchanged: requires both individual close prices unchanged.
    joint_age = flat_age(joint_flat, bid['close'], grid, sid, other_close=ask['close'])

    adjacent = np.zeros(n, dtype=bool)
    adjacent[1:] = (base[1:] & base[:-1]
                    & (sid[1:] == sid[:-1])
                    & (grid[1:] - grid[:-1] == MIN_NS))
    ret = np.full(n, np.nan)
    if adjacent.any():
        inds = np.flatnonzero(adjacent)
        ret[inds] = 10_000 * np.log(midpoint[inds]/midpoint[inds-1])

    status = np.full(n, 'BOTH_ABSENT', dtype='<U18')
    status[bid['present'] & ~ask['present']] = 'BID_ONLY'
    status[ask['present'] & ~bid['present']] = 'ASK_ONLY'
    status[paired & ~healthy] = 'INVALID_SIDE_OHLC'
    status[healthy] = 'PAIRED_VALID'
    status[crossed] = 'CROSSED_CLOSE'
    return dict(paired=paired, healthy=healthy, base=base, mid=midpoint, spread=spread,
                crossed=crossed, bid_age=b_age, ask_age=a_age, joint_age=joint_age,
                adjacent=adjacent, ret=ret, status=status,
                wide20=healthy & (spread > 20),
                wide50=healthy & (spread > 50),
                wide100=healthy & (spread > 100),
                jump=adjacent & (np.abs(ret) > jump_bp),
                screen15=base & (spread <= 50) & (joint_age < 15))


def run_tests():
    g = np.array([0, MIN_NS, 2*MIN_NS, 3*MIN_NS, 100*MIN_NS, 101*MIN_NS], dtype=np.int64)
    s = np.array([0,0,0,0,1,1], dtype=np.int32)
    a = np.array([True, True, False, True, True, True])
    ages = flat_age(a, np.array([5.,5.,np.nan,5.,5.,5.]), g, s)
    assert ages.tolist() == [1,2,0,1,1,2], ages
    assert flat_age(np.array([True,True]),np.array([2.,2.]),g[:2],s[:2]).tolist() == [1,2]
    def mk(closes, exists=None):
        vals = np.array(closes, dtype=np.float64)
        valid = np.ones(len(vals),dtype=bool)
        if exists is None: exists = valid.copy()
        return {k: vals.copy() for k in ('open','high','low','close')} | {'present':exists,'valid':valid}
    g2 = np.array([0,MIN_NS,2*MIN_NS,3*MIN_NS,4*MIN_NS], dtype=np.int64)
    sid = np.zeros(5,dtype=np.int32)
    bid = mk([100,100,100,100,100])
    ask = mk([100.10,100.10,100.10,100.10,100.10], np.array([True,True,False,True,True]))
    q = compute_quality(g2,sid,bid,ask,jump_bp=100.)
    assert q['status'].tolist() == ['PAIRED_VALID','PAIRED_VALID','BID_ONLY','PAIRED_VALID','PAIRED_VALID']
    assert q['joint_age'].tolist() == [1,2,0,1,2]
    assert np.isnan(q['ret'][3]) and np.isnan(q['ret'][2])  # no ffill over gap
    assert np.isfinite(q['ret'][1]) and np.isfinite(q['ret'][4])
    assert q['screen15'].sum()==4
    bad = mk([99.,99.,99.,99.,99.]);bad['present'][:] = True
    assert compute_quality(g2,sid,bid,bad,50)['crossed'].all()
    # A future change cannot alter a past-facing flag.
    modified = mk([100.10,100.10,100.10,100.20,100.30])
    assert (compute_quality(g2,sid,bid,modified,100)['joint_age'][:3] == [1,2,3]).all()
    assert iso(1_655_315_400_000_000_000).startswith('2022-06-15')
    # Unchanged midpoint caused by opposite quote side changes MUST reset joint age.
    bb = mk([100., 101., 100.]); aa = mk([102., 101., 102.])
    gg = np.array([0,MIN_NS,2*MIN_NS],dtype=np.int64); ss = np.zeros(3,dtype=np.int32)
    assert compute_quality(gg,ss,bb,aa,100)['joint_age'].tolist()==[1,1,1]
    print('SELF-TEST PASS: exact pairing, 1m gaps, session breaks, crossed close, causal freshness, UTC',flush=True)


def run_ledger(grid, sid, age, min_length=5, max_count=30):
    """RETROSPECTIVE runs. End-run length is not an at-time feature."""
    age = np.asarray(age)
    is_run = age > 0
    ending = is_run & (np.r_[age[1:], 0] != age + 1)
    end_pos = np.flatnonzero(ending & (age >= min_length))
    rows = []
    for i in end_pos:
        count = int(age[i]); start = i - count + 1
        rows.append(dict(start=iso(grid[start]), end=iso(grid[i]),
                         length_minutes=count, session=str(pd.Timestamp(grid[i], unit='ns', tz='UTC').tz_convert('America/New_York').date())))
    rows.sort(key=lambda x: x['length_minutes'],reverse=True)
    return rows[:max_count], len(end_pos)


def diagnostics(asset, grid, sid, b, a, q, out):
    n = len(grid)
    paired = q['paired'];healthy=q['healthy'];base=q['base']
    pair_sum = {
        'paired': int(paired.sum()),
        'bid_only': int((b['present'] & ~a['present']).sum()),
        'ask_only': int((a['present'] & ~b['present']).sum()),
        'neither': int((~b['present'] & ~a['present']).sum()),
        'spread_over_50': int(q['wide50'].sum()),
        'joint_age_ge15': int((q['joint_age'] >= 15).sum()),
    }
    warnings = {k: {'observed': pair_sum[k], 'expected_3_3': val}
                for k,val in EXPECTED_3_3[asset].items() if pair_sum[k] != val}
    runs, total_long_runs = run_ledger(grid,sid,q['joint_age'],5,40)

    close_spread = q['spread'][healthy]
    ret = q['ret'][q['adjacent']]
    stats = {
        'quote_files': {'bid':b['meta'],'ask':a['meta']},
        'rth_grid_minutes': int(n),
        'presence': pair_sum,
        'invalid_side_ohlc': int((paired & ~healthy).sum()),
        'crossed_close': int(q['crossed'].sum()),
        'paired_non_crossed_baseline': int(base.sum()),
        'spread_over_20bp': int(q['wide20'].sum()),
        'spread_over_100bp': int(q['wide100'].sum()),
        'spread_bps': {'median':float(np.median(close_spread)) if len(close_spread) else None,
                       'p99':float(np.percentile(close_spread,99)) if len(close_spread) else None,
                       'maximum':float(np.max(close_spread)) if len(close_spread) else None},
        'bid_past_flat_age_ge15':int((q['bid_age']>=15).sum()),
        'ask_past_flat_age_ge15':int((q['ask_age']>=15).sum()),
        'joint_past_flat_age_ge5':int((q['joint_age']>=5).sum()),
        'joint_past_flat_age_ge15':int((q['joint_age']>=15).sum()),
        'joint_past_flat_age_ge30':int((q['joint_age']>=30).sum()),
        'joint_past_flat_age_ge60':int((q['joint_age']>=60).sum()),
        'joint_flat_runs_ge5':total_long_runs,
        'longest_joint_flat_runs':runs[:15],
        'eligible_adjacent_1m_mid_returns':int(q['adjacent'].sum()),
        'midpoint_return_abs_gt_jump_threshold_count':int(q['jump'].sum()),
        'midpoint_return_abs_jump_threshold_bp':SOURCES[asset]['jump_bp'],
        'sensitivity_screen_spread50_flat15_pastonly':int(q['screen15'].sum()),
        'sensitivity_screen_retained_pct_of_baseline':float(q['screen15'].sum()/max(base.sum(),1)*100),
        'baseline_retained_unchanged':True,
        'warnings_vs_3_3':warnings,
    }
    # Fixed diagnostic episode, not a default exclusion rule.
    if asset == 'DOLLAR':
        start = pd.Timestamp('2022-06-15T18:01:00Z').value
        stop = pd.Timestamp('2022-06-15T19:03:00Z').value
        mask = (grid >= start) & (grid <= stop)
        idx = np.flatnonzero(mask)
        if len(idx):
            stats['june_15_2022_case'] = {
                'requested_utc_window':'2022-06-15 18:01–19:03 UTC',
                'scheduled_rth_minutes':int(len(idx)),
                'paired_minutes':int(paired[idx].sum()),
                'joint_flat_minutes':int((q['joint_age'][idx] > 0).sum()),
                'maximum_past_visible_joint_flat_age':int(q['joint_age'][idx].max()),
                'flat_at_first_minute':bool(q['joint_age'][idx[0]] > 0),
                'joint_flat_age_at_last_minute':int(q['joint_age'][idx[-1]]),
                'note':'Retrospective observed quotes; not confirmation that each candle is synthesized.'
            }

    # Preserve observed, one-sided and absent minutes, not only paired rows.
    panel = pd.DataFrame({
        'utc_minute_start': pd.to_datetime(grid, unit='ns', utc=True).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'status':q['status'],
        'bid_close':b['close'], 'ask_close':a['close'], 'mid_close':q['mid'],
        'spread_bp':np.round(q['spread'],5),
        'baseline_paired_non_crossed':base.astype(np.uint8),
        'bid_flat_age_past_only':q['bid_age'],
        'ask_flat_age_past_only':q['ask_age'],
        'joint_flat_age_past_only':q['joint_age'],
        'spread_gt50bp_flag':q['wide50'].astype(np.uint8),
        'mid_return_1m_bp_only_adjacent_paired':np.round(q['ret'],5),
        'mid_abs_jump_review_flag':q['jump'].astype(np.uint8),
        'sensitivity_spread50_flat15_eligible':q['screen15'].astype(np.uint8),
    })
    panel_path = out / f'quote_quality_rth_{asset}.csv.gz'
    panel.to_csv(panel_path, index=False, compression='gzip', na_rep='')
    del panel
    stats['output_panel'] = str(panel_path)

    # Candidate examples: widest spreads, largest legitimate adjacent-minute returns,
    # maximal past-visible flat ages. These are examples; no claimed independent verification.
    rows = []
    for label, values, eligible in (
        ('WIDEST_SPREAD',q['spread'],healthy),
        ('LARGEST_ABS_1M_RETURN',np.abs(q['ret']),q['adjacent']),
        ('LONGEST_FLAT_AT_MINUTE',q['joint_age'].astype(float),q['joint_age']>0)):
        ids = np.flatnonzero(eligible & np.isfinite(values))
        if len(ids):
            pick = ids[np.argsort(values[ids])[-25:]][::-1]
            for i in pick:
                rows.append({
                    'asset':asset,'reason':label,'utc_minute_start':iso(grid[i]),
                    'bid_close':float(b['close'][i]) if np.isfinite(b['close'][i]) else None,
                    'ask_close':float(a['close'][i]) if np.isfinite(a['close'][i]) else None,
                    'spread_bp':float(q['spread'][i]) if np.isfinite(q['spread'][i]) else None,
                    'mid_1m_return_bp':float(q['ret'][i]) if np.isfinite(q['ret'][i]) else None,
                    'joint_flat_age_past_only':int(q['joint_age'][i]),
                    'status':q['status'][i], 'independently_verified':False,
                })
    return stats, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test',action='store_true',help='Run built-in tests without reading sources')
    args=ap.parse_args()
    run_tests()
    if args.self_test:
        return
    OUTPUT.mkdir(parents=True, exist_ok=True)
    summary = {
        'section':'3.5 Dukascopy quote quality',
        'scope':'NYSE RTH minutes; source CSVs preserve all 24-hour observations for later overnight step',
        'input_timestamp':'UTC Unix milliseconds, minute-start labels',
        'midpoint_definition':'(bid CLOSE + ask CLOSE)/2 only for exact-minute matched, valid side OHLC; indicative asynchronous quote proxy',
        'default_action':'retain all observed quotes with flags; no synthetic detection claims, no auto-fill, no deletions',
        'causality':'past-only flat age, end-of-minute availability; top runs/examples are retrospective and forbidden as real-time features',
        'policies': {
            'baseline':'both sides exist, valid OHLC, ask CLOSE >= bid CLOSE; all positive spreads retained even if wide or flat',
            'secondary_sensitivity_only':'baseline AND close spread <= 50bp AND past-visible joint flat age < 15 minutes',
            'mid_return':'only exact adjacent minute paired baseline endpoints inside the same XNYS session',
            'not_verified':'individual synthetic candles, last-tick freshness, executable spread, independent spot reference, cross-provider quotes',
        },
        'assets':{}
    }
    examples = []
    for asset, spec in SOURCES.items():
        print(f'Building XNYS grid for {asset}...',flush=True)
        grid,sid,sessions=rth_grid(spec['begin'],spec['end'])
        print(f'{asset}: {len(sessions):,} sessions and {len(grid):,} RTH minutes',flush=True)
        print(f'{asset}: reading BID ({spec["bid"].name})...',flush=True)
        b=read_side(spec['bid'],grid)
        print(f'{asset}: reading ASK ({spec["ask"].name})...',flush=True)
        a=read_side(spec['ask'],grid)
        q=compute_quality(grid,sid,b,a,spec['jump_bp'])
        print(f'{asset}: paired {int(q["paired"].sum()):,}; flat age>=15 {int((q["joint_age"]>=15).sum()):,}',flush=True)
        asset_summary, case_rows=diagnostics(asset,grid,sid,b,a,q,OUTPUT)
        summary['assets'][asset]=asset_summary
        examples.extend(case_rows)
        if asset_summary['warnings_vs_3_3']:
            print(f'{asset}: WARNING: some reference counts differ from 3.3; see summary.json',flush=True)
        del b,a,q,grid,sid,sessions
    pd.DataFrame(examples).to_csv(OUTPUT/'quote_quality_cases.csv',index=False)
    (OUTPUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    lines=['# Section 3.5 — Gold/Dollar quote quality','',
        '**Scope:** exact UTC bid/ask pairing on XNYS RTH grid; no gap fill, no quote repair, no HMM. Full overnight source files remain intact for Section 3.7.','',
        '| Asset | Paired quotes | BID only | ASK only | Neither | Crossed close | Spread >50bp | Joint flat age >=15m |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for asset, st in summary['assets'].items():
        p=st['presence']
        lines.append(f'| {asset} | {p["paired"]:,} | {p["bid_only"]:,} | {p["ask_only"]:,} | {p["neither"]:,} | {st["crossed_close"]:,} | {p["spread_over_50"]:,} | {p["joint_age_ge15"]:,} |')
    lines+=['','## Further diagnostics','']
    for asset, st in summary['assets'].items():
        spread=st['spread_bps'];screen=st['sensitivity_screen_retained_pct_of_baseline']
        lines += [f'### {asset}',
          f'- Quote-close separation: median {spread["median"]:.3f}bp, p99 {spread["p99"]:.3f}bp, maximum {spread["maximum"]:.3f}bp.',
          f'- Per-side flat-age >=15m: BID {st["bid_past_flat_age_ge15"]:,}, ASK {st["ask_past_flat_age_ge15"]:,}; joint >=30m {st["joint_past_flat_age_ge30"]:,}, >=60m {st["joint_past_flat_age_ge60"]:,}.',
          f'- Adjacent valid minute midpoint returns: {st["eligible_adjacent_1m_mid_returns"]:,}; absolute >{st["midpoint_return_abs_jump_threshold_bp"]:g}bp candidates: {st["midpoint_return_abs_gt_jump_threshold_count"]:,}.',
          f'- Diagnostic strict sensitivity screen (<=50bp spread and joint past-flat age <15m) retains {screen:.3f}% of baseline paired observations.',
          f'- Top joint-stagnation case: {st["longest_joint_flat_runs"][0] if st["longest_joint_flat_runs"] else "none"}.',
        ]
        if st.get('june_15_2022_case'):
            lines.append(f'- June 15, 2022 documented flat-period check: {json.dumps(st["june_15_2022_case"])}')
        if st['warnings_vs_3_3']:
            lines.append(f'- **WARNING** differing from 3.3: {json.dumps(st["warnings_vs_3_3"])}')
        lines.append('')
    lines += [
        '## Interpretation and provisional policies','',
        '- **Known:** exact matching counts and recorded spread/flat-candle patterns, not actual tick-by-tick freshness.',
        '- **Not known:** whether any particular unchanged quote candle was synthesized by dukascopy-node; exporter mechanism has been demonstrated, not individual identity.',
        '- Large spreads can reflect price stress, asynchronous bid/ask quote closes, or data issues; numerical flags are diagnostics, not automatic corruption proofs.',
        '- Baseline midpoint is merely the midpoint of two minute CLOSE quotes, possibly with different last-tick times; it is not an executable midprice.',
        '- Freshness streak ages are strictly past-visible at their own minute end; retrospective longest-run outcomes must NEVER feed features.',
        '- In Section 3.6/3.10, compare baseline with predeclared strict quote sensitivity variants. Do not select a screen based on favorable HMM results.',
        '- No missing minute gets a manufactured zero return: 1m returns require two truly adjacent matched, baseline-eligible minutes.',
        '- Further independent historical tick verification, if obtainable, may resolve individual questionable quotes; otherwise note UNVERIFIED.',
        '', '## Output artifacts','',
        '- `quote_quality_rth_GOLD.csv.gz`, `quote_quality_rth_DOLLAR.csv.gz`: RTH indexed quote+quality panel (keep locally).',
        '- `quote_quality_cases.csv`: priority examples, including spread spikes, jumps and stale stretches.',
        '- `summary.json`: counts, trial policies, known/unknown boundaries. Original source data unchanged.',
    ]
    (OUTPUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'SUCCESS. Results: {OUTPUT}',flush=True)
    print('Upload REPORT.md, summary.json, quote_quality_cases.csv; keep large .csv.gz panels locally.',flush=True)


if __name__=='__main__':
    main()
