#!/usr/bin/env python3
"""Focused, READ-ONLY verification of eight unusually large Dukascopy minute returns.

Usage: python "$HOME\\Downloads\\section3_6_eight_jump_validation.py"
Outputs: ~/Downloads/section3_6_eight_jump_results/{REPORT.md,summary.json,jump_context.csv}

This diagnoses internal quote consistency; it CANNOT independently authenticate quotes.
Post-event data are RETROSPECTIVE REVIEW ONLY, never model features.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path.home() / 'OneDrive' / 'Desktop' / 'data' / 'raw'
OUTPUT = Path.home() / 'Downloads' / 'section3_6_eight_jump_results'
FILE_NAMES = {
 'GOLD': ('xauusd-m1-bid-2007-04-11-2026-10-02 - Copy.csv', 'xauusd-m1-ask-2007-04-11-2026-10-02.csv'),
 'DOLLAR': ('dollaridxusd-m1-bid-2017-12-01-2026-10-02.csv', 'dollaridxusd-m1-ask-2017-12-01-2026-10-02.csv')
}
EVENTS = {
 'GOLD': [('2026-01-29T15:27:00Z', -238.015700), ('2013-09-18T18:00:00Z', 137.674783),
          ('2013-12-18T19:00:00Z', -125.775839), ('2008-10-10T17:40:00Z', -104.163269)],
 'DOLLAR': [('2018-12-12T15:30:00Z', -73.848333), ('2019-06-12T14:30:00Z', -61.060187),
            ('2019-03-13T15:30:00Z', -55.477638), ('2022-11-02T18:36:00Z', 50.293181)]
}

def load_neighborhoods(path, events, minutes=15):
    if not path.exists():
        raise FileNotFoundError(f'Missing source CSV: {path}')
    centers = [int(pd.Timestamp(t).timestamp() * 1000) for t, _ in events]
    windows = [(t - minutes * 60_000, t + minutes * 60_000) for t in centers]
    parts = []
    for chunk in pd.read_csv(path, usecols=['timestamp', 'open','high','low','close'], chunksize=350_000):
        t = pd.to_numeric(chunk['timestamp'], errors='coerce')
        mask = np.zeros(len(chunk), dtype=bool)
        for start, stop in windows:
            mask |= t.between(start, stop).to_numpy()
        if mask.any():
            parts.append(chunk.loc[mask, ['timestamp','open','high','low','close']].copy())
    if not parts:
        return pd.DataFrame(columns=['timestamp','open','high','low','close']).set_index('timestamp')
    df = pd.concat(parts,ignore_index=True)
    df['timestamp'] = pd.to_numeric(df['timestamp'], errors='raise').astype('int64')
    if df.timestamp.duplicated().any():
        raise ValueError(f'Duplicate timestamps in {path.name}')
    return df.set_index('timestamp').sort_index()

def calc_bp(a,b):
    if pd.isna(a) or pd.isna(b) or a <= 0 or b <= 0:
        return None
    return float(10_000*np.log(b/a))

def evaluate(asset, stamp, reference_bp, bid, ask):
    ts = int(pd.Timestamp(stamp).timestamp()*1000)
    timeline = np.arange(ts-15*60_000, ts+16*60_000, 60_000,dtype='int64')
    df = pd.DataFrame({'ms':timeline})
    for side, original in [('bid',bid),('ask',ask)]:
        reindexed = original.reindex(timeline)
        for c in ['open','high','low','close']:
            df[f'{side}_{c}'] = pd.to_numeric(reindexed[c],errors='coerce').to_numpy()
    valid = df[['bid_close','ask_close']].notna().all(axis=1)
    df['mid'] = np.where(valid,(df.bid_close+df.ask_close)/2,np.nan)
    df['spread_bp'] = np.where(valid,10000*(df.ask_close-df.bid_close)/df.mid,np.nan)
    df['mid_ret_bp'] = 10000 * np.log(df.mid/df.mid.shift())
    df['bid_ret_bp'] = 10000 * np.log(df.bid_close/df.bid_close.shift())
    df['ask_ret_bp'] = 10000 * np.log(df.ask_close/df.ask_close.shift())
    df['relative_minute'] = np.arange(-15,16)
    df['asset'] = asset
    df['event_utc'] = stamp
    df['minute_utc'] = pd.to_datetime(df.ms,unit='ms',utc=True).dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    now = df.iloc[15]
    pre = df.iloc[14]
    p3 = df.iloc[18]
    p10 = df.iloc[25]
    def as_num(value):
        return None if pd.isna(value) else float(value)
    pre_run = 0
    for i in range(14, 0, -1):
        row,prev = df.iloc[i], df.iloc[i-1]
        if (pd.isna(row.bid_close) or pd.isna(row.ask_close) or
            not all(pd.notna(row[f'{side}_{c}']) and row[f'{side}_{c}']==row[f'{side}_close']
                    for side in ('bid','ask') for c in ('open','high','low','close')) or
            row.bid_close != prev.bid_close or row.ask_close != prev.ask_close):
            break
        pre_run += 1
    bid_move, ask_move = as_num(now.bid_ret_bp),as_num(now.ask_ret_bp)
    spread_before,spread_now = as_num(pre.spread_bp),as_num(now.spread_bp)
    row = {
      'asset':asset,'event_utc':stamp,'reference_bp':reference_bp,
      'reconstructed_mid_return_bp':as_num(now.mid_ret_bp),
      'reference_matches':bool(pd.notna(now.mid_ret_bp) and abs(now.mid_ret_bp-reference_bp)<0.02),
      'prior_paired':bool(pd.notna(pre.mid)), 'event_paired':bool(pd.notna(now.mid)),
      'bid_return_bp':bid_move,'ask_return_bp':ask_move,
      'bid_ask_move_discrepancy_bp':None if bid_move is None or ask_move is None else abs(bid_move-ask_move),
      'bid_ask_same_direction':None if bid_move is None or ask_move is None else bool(bid_move * ask_move > 0),
      'spread_before_bp':spread_before,'spread_event_bp':spread_now,
      'prior_visible_flat_minutes':pre_run,
      '3m_later_cumulative_from_pre_bp':calc_bp(pre.mid,p3.mid),
      '10m_later_cumulative_from_pre_bp':calc_bp(pre.mid,p10.mid),
      'remaining_window_paired_minutes':int(df.mid.notna().sum()),
      'has_31min_complete_context':bool(df.mid.notna().all()),
      'independent_tick_verification':'NOT_AVAILABLE',
    }
    # These labels are heuristic diagnostics, NOT evidence of authenticity.
    if not row['prior_paired'] or not row['event_paired']:
        row['internal_diagnostic'] = 'MISSING_ENDPOINT_CANNOT_RECONSTRUCT'
    elif not row['reference_matches']:
        row['internal_diagnostic'] = 'RECONSTRUCTION_MISMATCH'
    elif row['bid_ask_same_direction'] is False or row['bid_ask_move_discrepancy_bp'] > 0.2*abs(row['reconstructed_mid_return_bp']):
        row['internal_diagnostic'] = 'ASYMMETRIC_SIDES_REQUIRES_REVIEW'
    elif pre_run >= 5:
        row['internal_diagnostic'] = 'JUMP_AFTER_FLAT_STRETCH_REQUIRES_REVIEW'
    else:
        row['internal_diagnostic'] = 'BOTH_SIDES_REPRICE_TOGETHER_NOT_VERIFIED'
    return row,df

def self_test():
    base = 1_700_000_000_000
    d = pd.DataFrame({'timestamp':[base,base+60000], 'open':[100.0,101.0], 'high':[100.,101.], 'low':[100.,101.], 'close':[100.,101.]}).set_index('timestamp')
    assert round(calc_bp(100,101),4)==round(10000*np.log(1.01),4)
    assert calc_bp(float('nan'),101) is None
    assert d.reindex(np.array([base,base+60000,base+120000])).close.isna().iloc[-1]
    print('SELF-TEST PASS: log returns, missing endpoints, exact quote alignment')

def main():
    self_test()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    rows=[]; contexts=[]
    for asset,events in EVENTS.items():
        print(f'Loading focused quote windows: {asset}',flush=True)
        b=load_neighborhoods(ROOT/FILE_NAMES[asset][0],events)
        a=load_neighborhoods(ROOT/FILE_NAMES[asset][1],events)
        for stamp,bp in events:
            r,ctx=evaluate(asset,stamp,bp,b,a)
            rows.append(r);contexts.append(ctx)
            print(f"  {stamp}: {r['internal_diagnostic']}",flush=True)
    pd.concat(contexts,ignore_index=True).to_csv(OUTPUT/'jump_context.csv',index=False)
    pd.DataFrame(rows).to_csv(OUTPUT/'eight_jumps_review.csv',index=False)
    result={'section':'3.6 focused eight-event quote-return investigation',
            'method':'Original Dukascopy bid and ask CSVs; exact UTC minute-start event and +/-15m context',
            'events':rows,'not_done':'No independent tick-source verification; market news is contextual not trade authentication',
            'causality':'Post-event context is review-only; exclude it from any HMM features or at-event decisions.'}
    (OUTPUT/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    lines=['# Focused eight-extreme-return review','',
           '**Internal reconstruction only; no independent price or tick verification.**','',
           '| Asset | UTC minute | Return (bp) | Bid/ask agreement | Previous flat mins | Diagnostic |',
           '|---|---|---:|---|---:|---|']
    for r in rows:
        move='unavailable' if r['bid_ask_move_discrepancy_bp'] is None else f"difference {r['bid_ask_move_discrepancy_bp']:.2f} bp"
        v=r['reconstructed_mid_return_bp']
        lines.append(f"| {r['asset']} | {r['event_utc']} | {'NA' if v is None else f'{v:.2f}'} | {move} | {r['prior_visible_flat_minutes']} | {r['internal_diagnostic']} |")
    lines.extend(['','All extremes retained. Context and future reversion are *retrospective* diagnostics only.',
                  'No internal agreement test can prove that a quote was a genuine market-wide transaction.',
                  'Output `jump_context.csv` contains +/-15 minute bid/ask OHLC and returns for independent inspection.',
                  'Independent minute/tick evidence is still required to authenticate individual prints.'])
    (OUTPUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'SUCCESS. Upload REPORT.md, summary.json and eight_jumps_review.csv from {OUTPUT}',flush=True)

if __name__=='__main__':
    main()
