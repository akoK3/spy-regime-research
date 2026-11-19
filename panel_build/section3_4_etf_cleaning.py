#!/usr/bin/env python3
"""Section 3.4: Minimal-intervention ETF OHLCV baseline and causal diagnostics.

Read-only sources; writes only into Downloads/section3_4_etf_results.
Requires: pip install numpy pandas pandas_market_calendars
Usage: python "%USERPROFILE%\\Downloads\\section3_4_etf_cleaning.py"
Test:  python "%USERPROFILE%\\Downloads\\section3_4_etf_cleaning.py" --self-test

Important: the user must retain the 3.3 masks; this step writes observed ETF bars,
not a replacement full-grid mask. Do not treat diagnostics as deletion rules.
"""
from __future__ import annotations

import argparse
import json
import zipfile
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

HOME = Path.home()
DL = HOME / 'Downloads'
ROOT = HOME / 'OneDrive' / 'Desktop' / 'data' / 'raw'
OUT = DL / 'section3_4_etf_results'
ET = 'America/New_York'
MIN_NS = 60_000_000_000
CHUNK = 250_000
SPLICE = pd.Timestamp('2022-03-07', tz=ET).tz_convert('UTC').value
# REVIEW flags only. Neither cutoff is used to exclude an otherwise valid observation.
REVIEW_JUMP_BP = 200.0
REVIEW_INTRABAR_BP = 200.0

SOURCES = {
    'SPY_LEGACY': {'path': ROOT/'SPY_clean_1min.csv', 'ticker':'SPY', 'tag':'pitrading'},
    'TLT_LEGACY': {'path': ROOT/'TLT_clean_1min.csv', 'ticker':'TLT', 'tag':'pitrading'},
    'HYG_LEGACY': {'path': ROOT/'HYG_clean_1min.csv', 'ticker':'HYG', 'tag':'pitrading'},
    'SPY_RAW': {'path': DL/'hfdatalibrary_raw_1min_1tickers_2026-10-13.zip', 'ticker':'SPY', 'tag':'iex'},
    'TLT_RAW': {'path': DL/'hfdatalibrary_raw_1min_2tickers_2026-10-15.zip', 'ticker':'TLT', 'tag':'iex'},
    'HYG_RAW': {'path': DL/'hfdatalibrary_raw_1min_2tickers_2026-10-15.zip', 'ticker':'HYG', 'tag':'iex'},
}


def iso(n):
    return pd.Timestamp(int(n), unit='ns', tz='UTC').isoformat()


def exchange_grid():
    try:
        import pandas_market_calendars as mcal
        sessions = mcal.get_calendar('XNYS').schedule(start_date='2002-12-30', end_date='2026-10-14')
    except ImportError:
        try:
            import exchange_calendars as ec
            ex = ec.get_calendar('XNYS',start='2002-12-30',end='2026-10-14')
            sessions=ex.schedule.rename(columns={'open':'market_open','close':'market_close'})
        except ImportError as exc:
            raise SystemExit('Install calendar dependency: pip install pandas_market_calendars') from exc
    opens = pd.DatetimeIndex(sessions['market_open']).asi8
    closes = pd.DatetimeIndex(sessions['market_close']).asi8
    grid = np.concatenate([np.arange(a,b,MIN_NS,dtype=np.int64) for a,b in zip(opens,closes)])
    sess = np.searchsorted(opens, grid, side='right')-1
    assert (grid < closes[sess]).all()
    return grid, sess, sessions.index.strftime('%Y-%m-%d').to_numpy()


@contextmanager
def stream_source(spec):
    path=spec['path']
    if not path.is_file():
        raise FileNotFoundError(f'Missing source {path}')
    if path.suffix.lower()=='.zip':
        with zipfile.ZipFile(path) as z:
            filename=f"{spec['ticker']}_raw_1min.csv"
            member=next((n for n in z.namelist() if n.lower().endswith(filename.lower())),None)
            if not member:
                raise ValueError(f'{filename} missing in {path}')
            with z.open(member) as f:
                yield f, member
    else:
        with path.open('rb') as f:
            yield f, None


def stamp_ns(times):
    t=pd.to_datetime(times, format='%Y-%m-%d %H:%M:%S',errors='coerce')
    if t.isna().any():
        raise ValueError('Unparseable ETF timestamp(s)')
    return t.dt.tz_localize(ET, ambiguous='raise', nonexistent='raise').dt.tz_convert('UTC').astype('int64').to_numpy(np.int64)


def positions(ns,grid):
    p=np.searchsorted(grid,ns)
    yes=p<len(grid)
    result=np.zeros(len(ns),dtype=bool)
    result[yes]=grid[p[yes]]==ns[yes]
    return p,result


def validate(x):
    vals=x[['Open','High','Low','Close','Volume']].to_numpy(dtype=np.float64)
    o,h,l,c,v=vals.T
    return (np.isfinite(vals).all(axis=1) & (o>0)&(h>0)&(l>0)&(c>0)&(v>=0)
            & (h>=np.maximum(o,c)) &(l<=np.minimum(o,c))&(h>=l))


def compute_past_only_diagnostics(ns, sid, close, high, low, previous=None):
    """Sorted on-grid observations; previous=(ns,session,close,valid).

    Compare only to an IMMEDIATELY preceding scheduled minute in the same session.
    All computations for row t use current completed candle + past information.
    """
    n=len(ns)
    adjacent=np.zeros(n,dtype=bool)
    jump=np.full(n,np.nan)
    within=10000*np.log(high/low)
    if n:
        adjacent[1:] = (ns[1:]-ns[:-1]==MIN_NS)&(sid[1:]==sid[:-1])
        jump[1:] = np.where(adjacent[1:],10000*np.log(close[1:]/close[:-1]),np.nan)
        if previous is not None:
            prior_ns,prior_sid,prior_close = previous
            adjacent[0] = (ns[0]-prior_ns==MIN_NS) and (sid[0]==prior_sid)
            if adjacent[0]:
                jump[0] = 10000*np.log(close[0]/prior_close)
    return adjacent,jump,within


def save_chunk(df, file, first):
    df.to_csv(file,index=False,mode='w' if first else 'a',header=first,
              compression={'method':'gzip','compresslevel':1})


def process(name, spec, grid, sess, session_dates):
    global OUT
    outfile=OUT/f'etf_observed_{name}.csv.gz'
    off_file=OUT/f'etf_offcalendar_{name}.csv.gz'
    invalid_file=OUT/f'etf_invalid_{name}.csv.gz'
    first_main=first_off=first_bad=True
    seen=np.zeros(len(grid),dtype=bool)
    islegacy=name.endswith('_LEGACY')
    last_ns=None
    last_observed=None
    stats=dict(dataset=name, source=str(spec['path']), period='legacy' if islegacy else 'modern',
        source_label=spec['tag'], raw_rows=0, outside_epoch=0, off_calendar=0,
        valid_rth_rows=0, invalid_rth_rows=0, duplicates=0, zero_volume_rows=0,
        flagged_jump_review=0, flagged_range_review=0, suspicious_review_any=0,
        first_utc=None, last_utc=None, first_eligible_utc=None, last_eligible_utc=None,
        output=str(outfile.name), off_calendar_output=str(off_file.name),
        invalid_output=str(invalid_file.name))
    review_examples=[]
    with stream_source(spec) as (fh, member):
        required=['datetime','Open','High','Low','Close','Volume','source']
        head=pd.read_csv(fh,nrows=0)
        if not set(required).issubset(head.columns):
            raise ValueError(f'{name}: columns unexpected: {list(head.columns)}')
        fh.seek(0)
        for batch in pd.read_csv(fh,usecols=required,chunksize=CHUNK):
            batch=batch[batch['source'].astype(str).str.lower()==spec['tag']].copy()
            if batch.empty: continue
            stats['raw_rows']+=len(batch)
            ns=stamp_ns(batch['datetime'])
            inepoch = ns<SPLICE if islegacy else ns>=SPLICE
            stats['outside_epoch']+=int((~inepoch).sum())
            if not inepoch.all():
                raise RuntimeError(f'{name}: source tag includes records beyond expected provider boundary')
            # Files must already be in chronological order. Refuse silent sorting that might alter provenance.
            if len(ns)>1 and not (np.diff(ns)>0).all():
                raise RuntimeError(f'{name}: non-strict timestamp order or duplicates within chunk')
            if last_ns is not None and ns[0]<=last_ns:
                raise RuntimeError(f'{name}: non-strict order across chunks')
            last_ns=int(ns[-1])
            p,on=positions(ns,grid)
            stats['off_calendar']+=int((~on).sum())
            if (~on).any():
                off=batch.loc[~on].copy()
                off.insert(0,'utc_minute_start',pd.to_datetime(ns[~on],utc=True).strftime('%Y-%m-%dT%H:%M:%SZ'))
                off['reason']='OUTSIDE_SCHEDULED_XNYS_RTH'
                save_chunk(off,off_file,first_off);first_off=False
            if not on.any():continue
            p=p[on]
            if seen[p].any() or len(np.unique(p))!=len(p):
                stats['duplicates']+=int(seen[p].sum())
                raise RuntimeError(f'{name}: duplicate scheduled exchange timestamps')
            seen[p]=True
            x=batch.loc[on].reset_index(drop=True)
            xn=ns[on]
            session=sess[p]
            okay=validate(x)
            stats['invalid_rth_rows']+=int((~okay).sum())
            if (~okay).any():
                bad=x.loc[~okay].copy()
                bad.insert(0,'utc_minute_start',pd.to_datetime(xn[~okay],utc=True).strftime('%Y-%m-%dT%H:%M:%SZ'))
                bad['reason']='INVALID_NUMERIC_OHLCV'
                save_chunk(bad,invalid_file,first_bad);first_bad=False
            if not okay.any(): continue
            x=x.loc[okay].copy().reset_index(drop=True)
            xn=xn[okay];session=session[okay]
            ohlc=x[['Open','High','Low','Close','Volume']].to_numpy(dtype=np.float64)
            o,h,l,c,v=ohlc.T
            stats['zero_volume_rows']+=int((v==0).sum())
            adj,jump,intrabar=compute_past_only_diagnostics(xn,session,c,h,l,last_observed)
            # Keep no previous state across invalid bars except previous truly eligible bar
            last_observed=(int(xn[-1]),int(session[-1]),float(c[-1]))
            jflag=np.isfinite(jump)&(np.abs(jump)>REVIEW_JUMP_BP)
            rflag=intrabar>REVIEW_INTRABAR_BP
            stats['flagged_jump_review']+=int(jflag.sum())
            stats['flagged_range_review']+=int(rflag.sum())
            stats['suspicious_review_any']+=int((jflag|rflag).sum())
            dates=pd.to_datetime(xn,utc=True).strftime('%Y-%m-%dT%H:%M:%SZ')
            available=pd.to_datetime(xn+MIN_NS,utc=True).strftime('%Y-%m-%dT%H:%M:%SZ')
            data=pd.DataFrame({'utc_minute_start':dates,'earliest_available_utc_assuming_start_label':available,
                'session_date_ny':session_dates[session], 'ticker':spec['ticker'], 'source_epoch':spec['tag'],
                'Open':o,'High':h,'Low':l,'Close':c,'Volume':v,
                'volume_0_observed':(v==0).astype('uint8'),
                'adjacent_valid_prior_minute_same_session':adj.astype('uint8'),
                'causal_prev_minute_log_move_bp':jump,
                'bar_log_high_low_bp':intrabar,
                'review_move_gt_200bp':jflag.astype('uint8'),
                'review_range_gt_200bp':rflag.astype('uint8'),
                'numeric_ohlcv_valid':np.ones(len(xn),dtype='uint8'),
                'legacy_minute_start_assumed_unverified':np.full(len(xn),int(islegacy),dtype='uint8'),
            })
            save_chunk(data,outfile,first_main);first_main=False
            stats['valid_rth_rows']+=len(data)
            if stats['first_utc'] is None:stats['first_utc']=iso(xn[0])
            stats['last_utc']=iso(xn[-1])
            if stats['first_eligible_utc'] is None:stats['first_eligible_utc']=iso(xn[0]+MIN_NS)
            stats['last_eligible_utc']=iso(xn[-1]+MIN_NS)
            extreme=np.where(jflag|rflag)[0]
            if len(extreme):
                selected=data.iloc[extreme][['utc_minute_start','ticker','source_epoch','Open','High','Low','Close',
                    'causal_prev_minute_log_move_bp','bar_log_high_low_bp','review_move_gt_200bp','review_range_gt_200bp']].copy()
                selected['rank_bp']=np.nanmax(np.c_[np.abs(jump[extreme]),intrabar[extreme]],axis=1)
                review_examples.extend(selected.nlargest(12,'rank_bp').to_dict('records'))
                review_examples=sorted(review_examples,key=lambda r:r['rank_bp'],reverse=True)[:20]
    if not stats['valid_rth_rows']:
        raise RuntimeError(f'{name}: no valid RTH records: source missing or wrong date labels?')
    # Stable empty quarantine files; never imply off-calendar records were erased from inputs.
    basecols=['utc_minute_start','datetime','Open','High','Low','Close','Volume','source','reason']
    if first_off:save_chunk(pd.DataFrame(columns=basecols),off_file,True)
    if first_bad:save_chunk(pd.DataFrame(columns=basecols),invalid_file,True)
    print(f"{name}: eligible {stats['valid_rth_rows']:,}; outside RTH {stats['off_calendar']:,}; invalid {stats['invalid_rth_rows']:,}; review flags {stats['suspicious_review_any']:,}",flush=True)
    return stats,review_examples


def self_test():
    grid=np.array([0,MIN_NS,2*MIN_NS,3*MIN_NS,10*MIN_NS,11*MIN_NS],dtype=np.int64)
    sid=np.array([0,0,0,0,1,1])
    p,yes=positions(np.array([0,2*MIN_NS,4*MIN_NS,10*MIN_NS]),grid)
    assert yes.tolist()==[True,True,False,True]
    assert p.tolist()==[0,2,4,4]
    x=pd.DataFrame({'Open':[100,100], 'High':[100,102.5], 'Low':[100,100], 'Close':[100,102.5], 'Volume':[0,9]})
    assert validate(x).tolist()==[True,True]
    ns=np.array([0,MIN_NS,3*MIN_NS,10*MIN_NS,11*MIN_NS],dtype=np.int64)
    s=np.array([0,0,0,1,1])
    close=np.array([100,102.5,115,101,104],dtype=float)
    h=close.copy();l=close.copy()
    adj,jump,within=compute_past_only_diagnostics(ns,s,close,h,l)
    assert adj.tolist()==[False,True,False,False,True],adj
    assert jump[1]>200 and np.isnan(jump[2]) and np.isnan(jump[3]) and np.isfinite(jump[4])
    assert np.all(within==0)
    # Cross-chunk check: consecutive only within same session.
    a,j,r=compute_past_only_diagnostics(np.array([MIN_NS]),np.array([0]),np.array([102.5]),
                np.array([102.5]),np.array([102.5]),(0,0,100.0))
    assert a[0] and j[0]>200
    a,j,r=compute_past_only_diagnostics(np.array([10*MIN_NS]),np.array([1]),np.array([100.0]),
                np.array([100.0]),np.array([100.0]),(3*MIN_NS,0,98.0))
    assert not a[0] and np.isnan(j[0])
    # Bad OHLC cannot enter output panel.
    y=x.copy();y.loc[1,'High']=99.0
    assert validate(y).tolist()==[True,False]
    print('SELF-TEST PASS: schedule match, zero volume retention, invalid OHLC quarantine, no gap/session return bridging, causal review flags')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    self_test()
    if args.self_test:return
    OUT.mkdir(parents=True,exist_ok=True)
    grid,sid,dates=exchange_grid()
    print(f'XNYS calendar: {len(grid):,} RTH minute labels',flush=True)
    summary={'section':'3.4 ETF Cleaning', 'approach':'Minimal intervention; causal diagnostics only',
             'review_threshold_bp':{'jump':REVIEW_JUMP_BP,'bar_range':REVIEW_INTRABAR_BP},
             'primary_policy': ['Keep valid observed PiTrading historic and modern IEX RAW bars on XNYS RTH grid',
                'Do not interpolate, forward fill, or create synthetic missing ETF observations',
                'Isolate off-RTH records for separate review; do not destroy source rows',
                'Quarantine truly invalid numeric OHLCV records, with original rows saved',
                'Keep 200bp review flags; do not remove flagged large valid price moves',
                'Do not merge raw volume across source epochs or use centered cleaning windows',
                'Earliest candle availability = start label plus 1 minute; legacy timing conditional'],
             'dataset':{},'notes':[]}
    reviews=[]
    for name,spec in SOURCES.items():
        print('Loading',name,'...',flush=True)
        status, examples=process(name,spec,grid,sid,dates)
        summary['dataset'][name]=status
        reviews.extend(examples)
    examples=sorted(reviews,key=lambda r:r['rank_bp'],reverse=True)[:40]
    pd.DataFrame(examples,columns=['utc_minute_start','ticker','source_epoch','Open','High','Low','Close',
                'causal_prev_minute_log_move_bp','bar_log_high_low_bp','review_move_gt_200bp',
                'review_range_gt_200bp','rank_bp']).to_csv(OUT/'review_cases_top40.csv',index=False)
    with (OUT/'summary.json').open('w',encoding='utf-8') as f:json.dump(summary,f,indent=2)
    lines=['# Section 3.4 — ETF cleaning (minimal intervention)','',
        '**Purpose:** Preserve observed trustworthy price bars while flagging—not automatically deleting—candidate extremes. No HMM or cross-asset leakage study.', '',
        '| Dataset | Eligible observed RTH | Off RTH (separate) | Invalid OHLCV | Zero volume (retained) | Review flags (>200bp) |',
        '|---|---:|---:|---:|---:|---:|']
    for name,d in summary['dataset'].items():
        lines.append(f"| {name} | {d['valid_rth_rows']:,} | {d['off_calendar']:,} | {d['invalid_rth_rows']:,} | {d['zero_volume_rows']:,} | {d['suspicious_review_any']:,} |")
    lines.extend(['','## Adopted rules','',
        '- Primary retained population: valid OHLCV, exact XNYS scheduled regular-session minute, correct provider epoch.',
        '- Excluded from primary regular-session panel: off-RTH records (stored separately) and demonstrably invalid numeric OHLCV (stored separately).',
        '- **No automatic exclusion of valid unusually large returns or price ranges.** 200bp = diagnostic triage threshold only.',
        '- No missing-minute forward fill, interpolation, or restoration. Section 3.3 mask is the authoritative full-grid record.',
        '- `causal_prev_minute_log_move_bp` exists only when the prior scheduled minute in the same session had an eligible observed bar; do not call multi-minute gap movement a one-minute return.',
        '- Every bar has an *earliest available* timestamp at the end of its minute, conditional on the unverified historical labeling convention.',
        '- Source-specific volumes preserved as raw numbers; historical and IEX trade-volume scales are not pooled.',
        '- Current RAW IEX vs older CLEAN comparisons and dividend basis are NOT used as cleaning criteria.',
        '', '## Open limitations', '',
        '- Pre-2022 PiTrading filtering mechanism and candle boundaries remain unknown; awaiting vendor clarification.',
        '- Some seemingly anomalous valid bars may reflect true volatility; others may be vendor errors. Diagnostic flags do not adjudicate each case.',
        '- Modern IEX RAW bars reflect one venue; absence is not proof of no market-wide trades.',
        '- ETF ex-dividend distributions and overnight adjustments are treated later (3.7–3.8).',
        '', '## Artifacts', '',
        '- `etf_observed_*.csv.gz`: retained observed ETF bars and causal flags; one row per source RTH label.',
        '- `etf_offcalendar_*.csv.gz`: observed out-of-RTH rows preserved for inspection.',
        '- `etf_invalid_*.csv.gz`: observed RTH records excluded for objectively invalid OHLCV.',
        '- `review_cases_top40.csv`: extreme candidate examples for manual inspection; **not removed**.',
        '- `summary.json`: counts and decisions. Original inputs remain unchanged.',
        '', '**Next:** Review counts and extreme examples; only if unexplained gross anomalies exist, carry forward focused checks. Otherwise freeze 3.4 and proceed to 3.5.'])
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('SUCCESS. Please upload REPORT.md, summary.json, and review_cases_top40.csv from:',OUT,flush=True)

if __name__=='__main__':main()
