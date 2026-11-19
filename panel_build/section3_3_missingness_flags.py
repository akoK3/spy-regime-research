#!/usr/bin/env python3
"""Research Section 3.3 — missing-observation masks and gap ledger (READ ONLY).

Requirements: python -m pip install numpy pandas pandas_market_calendars
Run on user's Windows PC: python "%USERPROFILE%\\Downloads\\section3_3_missingness_flags.py"
Self-check: python "%USERPROFILE%\\Downloads\\section3_3_missingness_flags.py" --self-test

IMPORTANT: Output flags are observations, NOT proof of the reasons for missing
trade/quote source data. No interpolation, gap filling, filtering, or models.
Earlier HF CLEAN and later RAW have different archive dates (rebuild confounding).
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HOME = Path.home()
DL = HOME / 'Downloads'
ROOT = HOME / 'OneDrive' / 'Desktop' / 'data' / 'raw'
OUT = DL / 'section3_3_missingness_results'
ET = 'America/New_York'
MIN_NS = 60_000_000_000
CHUNK = 350_000
CAL_START = '2002-12-30'
CAL_END = '2026-10-14'
# A documented source-wide episode. It does not prove the individual reason for each absent bar.
KNOWN_HF_SESSION = '2024-12-23'

ETF_SPEC = {
    'SPY_LEGACY': dict(path=ROOT/'SPY_clean_1min.csv', tag='pitrading', symbol='SPY'),
    'TLT_LEGACY': dict(path=ROOT/'TLT_clean_1min.csv', tag='pitrading', symbol='TLT'),
    'HYG_LEGACY': dict(path=ROOT/'HYG_clean_1min.csv', tag='pitrading', symbol='HYG'),
    'SPY_RAW': dict(path=DL/'hfdatalibrary_raw_1min_1tickers_2026-10-13.zip', symbol='SPY'),
    'TLT_RAW': dict(path=DL/'hfdatalibrary_raw_1min_2tickers_2026-10-15.zip', symbol='TLT'),
    'HYG_RAW': dict(path=DL/'hfdatalibrary_raw_1min_2tickers_2026-10-15.zip', symbol='HYG'),
    'SPY_OLD_CLEAN': dict(path=ROOT/'SPY_clean_1min.csv', tag='iex', symbol='SPY'),
    'TLT_OLD_CLEAN': dict(path=ROOT/'TLT_clean_1min.csv', tag='iex', symbol='TLT'),
    'HYG_OLD_CLEAN': dict(path=ROOT/'HYG_clean_1min.csv', tag='iex', symbol='HYG'),
}
QUOTE_SPEC = {
    'GOLD': (
        ROOT/'xauusd-m1-bid-2007-04-11-2026-10-02 - Copy.csv',
        ROOT/'xauusd-m1-ask-2007-04-11-2026-10-02.csv',
        '2007-04-11', '2026-10-01'),
    'DOLLAR': (
        ROOT/'dollaridxusd-m1-bid-2017-12-01-2026-10-02.csv',
        ROOT/'dollaridxusd-m1-ask-2017-12-01-2026-10-02.csv',
        '2017-12-01', '2026-10-01'),
}


def iso_utc(v):
    return pd.Timestamp(int(v), unit='ns', tz='UTC').isoformat()


def calendar():
    try:
        import pandas_market_calendars as mcal
        sessions = mcal.get_calendar('XNYS').schedule(start_date=CAL_START, end_date=CAL_END)
    except ImportError:
        try:
            import exchange_calendars as ec
            ex=ec.get_calendar('XNYS', start=CAL_START, end=CAL_END)
            sessions=ex.schedule.rename(columns={'open':'market_open','close':'market_close'})
        except ImportError as exc:
            raise SystemExit('Install dependency: python -m pip install pandas_market_calendars') from exc
    opening = pd.DatetimeIndex(sessions['market_open']).asi8
    closing = pd.DatetimeIndex(sessions['market_close']).asi8
    grid = np.concatenate([np.arange(a, b, MIN_NS, dtype=np.int64) for a, b in zip(opening, closing)])
    if not (2_000_000 < len(grid) < 2_500_000):
        raise RuntimeError('NYSE grid incorrect; expected ~2.3 million minute starts')
    sid = np.searchsorted(opening, grid, side='right') - 1
    assert np.all(grid < closing[sid])
    dates = sessions.index.strftime('%Y-%m-%d').to_numpy()
    print(f'NYSE grid: {len(sessions):,} sessions, {len(grid):,} scheduled RTH minutes', flush=True)
    return grid, sid, dates, sessions


@contextmanager
def data_stream(spec):
    path = spec['path']
    if not path.is_file():
        raise FileNotFoundError(f'Expected file missing: {path}')
    if path.suffix.lower() == '.zip':
        with zipfile.ZipFile(path) as z:
            member = next((n for n in z.namelist() if n.lower().endswith(f"{spec['symbol'].lower()}_raw_1min.csv")), None)
            if member is None:
                raise RuntimeError(f'Cannot find {spec["symbol"]} RAW CSV in {path}')
            with z.open(member) as f:
                yield f, str(path), member
    else:
        with path.open('rb') as f:
            yield f, str(path), None


def parse_etf_dates(source):
    ts = pd.to_datetime(source, format='%Y-%m-%d %H:%M:%S', errors='coerce')
    if ts.isna().any():
        raise ValueError('Malformed ETF timestamps encountered')
    ts = ts.dt.tz_localize(ET, ambiguous='raise', nonexistent='raise').dt.tz_convert('UTC')
    return ts.astype('int64').to_numpy(np.int64)


def index_to_grid(ns, grid):
    pos = np.searchsorted(grid, ns)
    valid = pos < len(grid)
    result = np.zeros(len(pos), dtype=bool)
    result[valid] = grid[pos[valid]] == ns[valid]
    return pos, result


def valid_ohlc(frame):
    arr = frame[['Open', 'High', 'Low', 'Close', 'Volume']].to_numpy(dtype=np.float64)
    o,h,l,c,v = (arr[:,i] for i in range(5))
    return (np.isfinite(arr).all(axis=1) & (o>0)&(h>0)&(l>0)&(c>0)&(v>=0)
            & (h>=np.maximum(o,c)) & (l<=np.minimum(o,c)) & (h>=l))


def load_etf(name, spec, grid):
    present = np.zeros(len(grid), dtype=bool)
    healthy = np.zeros(len(grid), dtype=bool)
    info = {'name':name,'path':str(spec['path']),'rows_source_subset':0, 'off_calendar':0,
            'off_calendar_examples_utc':[], 'duplicate_on_grid':0, 'invalid_ohlc_rows':0}
    with data_stream(spec) as (fh, filepath, member):
        info['path'] = filepath
        info['zip_member'] = member
        head = pd.read_csv(fh, nrows=0)
        cols = list(head.columns)
        required = ['datetime', 'Open', 'High', 'Low', 'Close', 'Volume']
        if any(c not in cols for c in required):
            raise ValueError(f'{name}: unexpected columns {cols}')
        use = required + (['source'] if spec.get('tag') else [])
        fh.seek(0)
        for part in pd.read_csv(fh, usecols=use, chunksize=CHUNK):
            if spec.get('tag'):
                part = part[part['source'].astype(str).str.lower().eq(spec['tag'])]
            if part.empty:
                continue
            info['rows_source_subset'] += len(part)
            ns = parse_etf_dates(part['datetime'])
            loc, good = index_to_grid(ns, grid)
            info['off_calendar'] += int((~good).sum())
            if len(info['off_calendar_examples_utc']) < 8:
                info['off_calendar_examples_utc'].extend(
                    [iso_utc(n) for n in ns[~good][:8-len(info['off_calendar_examples_utc'])]])
            if not np.any(good):
                continue
            positions = loc[good]
            info['duplicate_on_grid'] += int(present[positions].sum())
            if len(np.unique(positions)) != len(positions):
                raise RuntimeError(f'{name}: duplicate within a CSV chunk')
            if info['duplicate_on_grid']:
                raise RuntimeError(f'{name}: duplicate time labels found')
            present[positions] = True
            ok = valid_ohlc(part)
            info['invalid_ohlc_rows'] += int((~ok).sum())
            healthy[positions] = ok[good]
    if not present.any():
        raise RuntimeError(f'{name}: zero observations on NYSE grid; check timezone/source')
    where = np.flatnonzero(present)
    info['first_utc'] = iso_utc(grid[where[0]])
    info['last_utc'] = iso_utc(grid[where[-1]])
    info['first_pos'],info['last_pos'] = int(where[0]),int(where[-1])
    info['observed_rth'] = int(len(where))
    print(f'{name}: {info["observed_rth"]:,} exchange-minute labels; off calendar {info["off_calendar"]:,}', flush=True)
    return present, healthy, info


def age_and_runs(grid, sid, observed):
    """Run-length only for missing rows; time since previous observed within session.

    Uses an exchange-minute clock. Never bridges distinct sessions.
    """
    n=len(grid)
    if n==0:
        return np.empty(0, dtype=np.int32), np.empty(0,dtype=np.int32), np.empty(0,dtype=bool), np.empty(0,dtype=bool), []
    same_prev = np.r_[False, sid[1:]==sid[:-1]]
    immediate = np.r_[False, observed[:-1] & same_prev[1:]]
    # previous observed row with same session (not necessarily immediately adjacent)
    seen = np.maximum.accumulate(np.where(observed,np.arange(n,dtype=np.int32),-1))
    prev = np.r_[-1, seen[:-1]]
    validprev=(prev>=0)
    validprev[validprev] &= sid[prev[validprev]]==sid[np.flatnonzero(validprev)]
    elapsed = np.full(n,-1,dtype=np.int32)
    sel=np.flatnonzero(validprev)
    elapsed[sel]=((grid[sel]-grid[prev[sel]])//MIN_NS).astype(np.int32)
    missing=~observed
    run_start = missing & np.r_[True, (~missing[:-1]) | (~same_prev[1:])]
    run_end = missing & np.r_[(~missing[1:]) | (sid[1:]!=sid[:-1]), True]
    starts=np.flatnonzero(run_start)
    ends=np.flatnonzero(run_end)
    if len(starts)!=len(ends):
        raise RuntimeError('Missing run markers inconsistent')
    lengths = np.zeros(n, dtype=np.int32)
    runs=[]
    for lo,hi in zip(starts,ends):
        count=int(hi-lo+1)
        lengths[lo:hi+1] = count
        runs.append((int(lo),int(hi),count))
    return lengths,elapsed,validprev,immediate,runs


def write_mask(path, grid, sid, dates, observed, healthy, status, disruption,
               extra=None, name=None):
    lengths,elapsed,hasprevious,immediate,runs=age_and_runs(grid,sid,observed)
    local = pd.to_datetime(grid, utc=True).strftime('%Y-%m-%dT%H:%M:%SZ')
    data = {
        'utc_minute_start':local,
        'session_date_ny':dates[sid],
        'status':status,
        'observed':observed.astype('uint8'),
        'valid_numeric_ohlc':healthy.astype('uint8'),
        'known_hf_disruption':disruption.astype('uint8'),
        'missing_run_length':lengths,
        'minutes_since_prior_observed':elapsed,
        'prior_observation_same_session':hasprevious.astype('uint8'),
        'immediately_prior_minute_observed':immediate.astype('uint8'),
    }
    if extra:
        data.update(extra)
    pd.DataFrame(data).to_csv(path,index=False,compression={'method':'gzip','compresslevel':1})
    gap_rows = []
    for lo,hi,count in runs:
        gap_rows.append(dict(dataset=name, start_utc=local[lo], end_utc=local[hi],
                             session_date_ny=dates[sid[lo]], missing_minutes=count,
                             type=(status[lo] if np.all(status[lo:hi+1]==status[lo]) else 'MIXED_STATUS'), known_hf_disruption=int(disruption[lo])))
    gap_name=OUT/f'gaps_{name}.csv.gz'
    pd.DataFrame(gap_rows,columns=['dataset','start_utc','end_utc','session_date_ny',
                                    'missing_minutes','type','known_hf_disruption']).to_csv(
                                        gap_name,index=False,compression={'method':'gzip','compresslevel':1})
    return {'minutes':int(len(grid)),'observed':int(observed.sum()),
            'missing':int((~observed).sum()), 'invalid_present':int((observed & ~healthy).sum()),
            'gap_runs':int(len(runs)),'longest_gap':int(max([r[2] for r in runs],default=0)),
            'disruption_missing':int(((~observed)&disruption).sum()),
            'mask_file':path.name,'gap_file':gap_name.name}


def classify_etf(name, observed, base_raw=None):
    status=np.full(len(observed),'OBSERVED',dtype='<U36')
    if name.endswith('_LEGACY'):
        status[~observed] = 'LEGACY_ABSENT_UNKNOWN'
    elif name.endswith('_RAW'):
        status[~observed] = 'IEX_RAW_NO_BAR_CAUSE_UNCONFIRMED'
    else:
        if base_raw is None:
            raise RuntimeError('Comparison RAW required for old clean')
        status[(~observed) & base_raw] = 'RAW_PRESENT_OLD_CLEAN_ABSENT'
        status[(~observed) & ~base_raw] = 'NO_RAW_BAR'
    return status


def read_quote_side(file, grid):
    if not file.exists():
        raise FileNotFoundError(str(file))
    n=len(grid)
    present=np.zeros(n,dtype=bool)
    healthy=np.zeros(n,dtype=bool)
    # float64 values for observed exchange minutes only
    o=np.full(n,np.nan); h=np.full(n,np.nan); l=np.full(n,np.nan); c=np.full(n,np.nan)
    total=0
    offcalendar=0
    duplicates=0
    for df in pd.read_csv(file,usecols=['timestamp','open','high','low','close'],chunksize=CHUNK):
        total+=len(df)
        stamp = pd.to_numeric(df['timestamp'],errors='coerce')
        if stamp.isna().any() or (stamp < 10**11).any() or (stamp > 10**14).any():
            raise ValueError(f'{file}: unsupported/malformed Unix-millisecond timestamps')
        ns=stamp.astype('int64').to_numpy()*1_000_000
        pos, ongrid=index_to_grid(ns,grid)
        offcalendar += int((~ongrid).sum())
        if not ongrid.any():
            continue
        p=pos[ongrid]
        duplicates += int(present[p].sum())
        if duplicates or len(p)!=len(np.unique(p)):
            raise ValueError(f'{file}: duplicate minute label')
        arr=df[['open','high','low','close']].to_numpy(dtype=np.float64)[ongrid]
        x,y,z,w=arr.T
        ok=np.isfinite(arr).all(axis=1)&(x>0)&(y>0)&(z>0)&(w>0)&(y>=np.maximum(x,w))&(z<=np.minimum(x,w))
        present[p]=True; healthy[p]=ok
        o[p]=x; h[p]=y; l[p]=z; c[p]=w
    info={'filename':str(file),'rows_total':int(total),'rows_rth':int(present.sum()),
          'off_rth_including_valid_overnight':offcalendar,'rth_invalid_ohlc':int((present & ~healthy).sum())}
    print(f'  {file.name}: {total:,} total, {present.sum():,} RTH minute labels',flush=True)
    return dict(present=present,healthy=healthy,open=o,high=h,low=l,close=c,info=info)


def quote_quality(grid,sid,bid,ask):
    bp=bid['present'];ap=ask['present'];paired=bp&ap
    healthy=paired & bid['healthy'] & ask['healthy']
    spread=np.full(len(grid),np.nan)
    midpoint=(bid['close']+ask['close'])/2
    spread[healthy]=10000*(ask['close'][healthy]-bid['close'][healthy])/midpoint[healthy]
    negative=healthy & (spread<0)
    wide=healthy & (spread>50)  # diagnostic threshold only; NOT a deletion rule
    joint_flat=healthy.copy()
    for side in (bid,ask):
        joint_flat &= (side['open']==side['high']) & (side['high']==side['low']) & (side['low']==side['close'])
    age=np.zeros(len(grid),dtype=np.int32)
    # Past-observed minute-by-minute age only. Never use eventual future-known length.
    for i in np.flatnonzero(joint_flat):
        if (i>0 and sid[i]==sid[i-1] and grid[i]-grid[i-1]==MIN_NS and joint_flat[i-1]
                and bid['close'][i] == bid['close'][i-1]
                and ask['close'][i] == ask['close'][i-1]):
            age[i]=age[i-1]+1
        else:
            age[i]=1
    return paired, healthy, spread, negative, wide, age


def run_tests():
    # Early session opens and early closes are handled on real exchange minute grid.
    try:
        import pandas_market_calendars as mcal
        sch=mcal.get_calendar('XNYS').schedule(start_date='2024-11-29',end_date='2024-11-29')
    except ImportError:
        import exchange_calendars as ec
        sch=ec.get_calendar('XNYS',start='2024-11-29',end='2024-12-02').schedule.rename(columns={'open':'market_open','close':'market_close'})
    assert len(sch)>=1
    assert (sch.iloc[0]['market_close']-sch.iloc[0]['market_open']).total_seconds()==210*60
    grid=np.array([0,MIN_NS,2*MIN_NS,3*MIN_NS,100*MIN_NS,101*MIN_NS],dtype=np.int64)
    sid=np.array([0,0,0,0,1,1])
    obs=np.array([True,False,False,True,False,True])
    lengths, elapsed, prev, immediate,runs=age_and_runs(grid,sid,obs)
    assert lengths.tolist()==[0,2,2,0,1,0],lengths
    assert elapsed.tolist()==[-1,1,2,3,-1,-1],elapsed
    assert len(runs)==2 and runs[0][2]==2 and runs[1][2]==1
    test_ns=np.array([1_735_000_000_000],dtype=np.int64)*1_000_000
    assert pd.to_datetime(test_ns[0],unit='ns',utc=True).year==2024
    def side(vals,st):
        return dict(present=np.ones(4,dtype=bool),healthy=np.ones(4,dtype=bool),
             open=np.array(vals,dtype=float), high=np.array(vals,dtype=float),
             low=np.array(vals,dtype=float), close=np.array(vals,dtype=float))
    b=side([100,100,100,100],None);a=side([100.01,100.01,100.01,100.01],None)
    qgrid=np.arange(4,dtype=np.int64)*MIN_NS
    paired,valid,sp,neg,wide,ages=quote_quality(qgrid,np.zeros(4,dtype=np.int32),b,a)
    assert ages.tolist()==[1,2,3,4] and paired.all() and valid.all() and not wide.any()
    a['close'][:]=99.;a['open'][:]=99.;a['high'][:]=99.;a['low'][:]=99.
    assert quote_quality(qgrid,np.zeros(4,dtype=np.int32),b,a)[3].all()
    c=classify_etf('SPY_OLD_CLEAN',np.array([True,False,False]),np.array([True,True,False]))
    assert c.tolist()==['OBSERVED','RAW_PRESENT_OLD_CLEAN_ABSENT','NO_RAW_BAR'],c
    print('SELF-TEST PASS: early close, session gap, UTC ms->ns, causal flat-age, spread, CLEAN comparison',flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    run_tests()
    if args.self_test:
        return
    OUT.mkdir(parents=True,exist_ok=True)
    grid,sid,dates,sessions=calendar()
    # All rows in this table are scheduled tradable minutes; hours outside grid are NOT "missing".
    pd.DataFrame(dict(session_date_ny=dates,
         market_open_utc=pd.DatetimeIndex(sessions['market_open']).strftime('%Y-%m-%dT%H:%M:%SZ'),
         market_close_utc=pd.DatetimeIndex(sessions['market_close']).strftime('%Y-%m-%dT%H:%M:%SZ'))).to_csv(
            OUT/'exchange_sessions.csv',index=False)
    disruption=(dates[sid]==KNOWN_HF_SESSION)
    summary={'section':'3.3 Missing-data identification; not cleaning','calendar':'XNYS 09:30-16:00 adjusted for holidays and early closes',
             'assumptions':['ETF labels America/New_York; legacy minute-start UNCERTAIN','Quote timestamps Unix milliseconds UTC minute-start',
                'Outside-exchange-hours not treated as missing','No causality inferred from file absence'],
             'datasets':{},'quotes':{},'comparison':{},'classification_rules':{}}
    etf_presence={}
    # Load RAW first, then historical, then old CLEAN. Retain only on-grid booleans in memory.
    order=['SPY_RAW','TLT_RAW','HYG_RAW','SPY_LEGACY','TLT_LEGACY','HYG_LEGACY',
           'SPY_OLD_CLEAN','TLT_OLD_CLEAN','HYG_OLD_CLEAN']
    for name in order:
        print(f'Loading {name}...',flush=True)
        p,ok,info=load_etf(name,ETF_SPEC[name],grid)
        lo=info['first_pos']
        # Include the entire FINAL scheduled session, even if the source's final 15:59 is absent.
        # At the very first recorded session, start at the first recorded minute (sample begins there).
        hi=int(np.searchsorted(sid, sid[info['last_pos']], side='right'))
        sub=grid[lo:hi]; subs=sid[lo:hi]
        # OLD CLEAN end of data sometimes lacks final 15:59 bar; don't mislabel a nonexistent later session.
        companion=etf_presence.get(name.split('_')[0]+'_RAW') if name.endswith('_OLD_CLEAN') else None
        status=classify_etf(name,p[lo:hi],companion[lo:hi] if companion is not None else None)
        flags=write_mask(OUT/f'masks_{name}.csv.gz',sub,subs,dates,p[lo:hi],ok[lo:hi],status,
                         disruption[lo:hi] if not name.endswith('_LEGACY') else np.zeros(len(sub),dtype=bool),
                         name=name)
        summary['datasets'][name]={**info,**flags}
        etf_presence[name]=p
        if name.endswith('_OLD_CLEAN') and companion is not None:
            m=~p[lo:hi];raw_present=companion[lo:hi]
            summary['comparison'][name]={
                'raw_present_old_clean_absent':int((m & raw_present).sum()),
                'raw_absent_old_clean_absent':int((m & ~raw_present).sum()),
                'clean_without_raw':int((p[lo:hi]&~raw_present).sum()),
                'caution':'RAW and old CLEAN are different vintage releases; do not assert causal cleaner attribution'}
        del p,ok
    del etf_presence
    for asset,(bidfile,askfile,first,last) in QUOTE_SPEC.items():
        print(f'Loading quotes for {asset}...',flush=True)
        bid=read_quote_side(bidfile,grid)
        ask=read_quote_side(askfile,grid)
        lo=np.searchsorted(grid,pd.Timestamp(first,tz='America/New_York').tz_convert('UTC').value,side='left')
        hi=np.searchsorted(grid,pd.Timestamp(last,tz='America/New_York').tz_convert('UTC').value + 24*60*MIN_NS,side='left')
        qgrid=grid[lo:hi]; qsid=sid[lo:hi]
        b={k:(v[lo:hi] if isinstance(v,np.ndarray) else v) for k,v in bid.items()}
        a={k:(v[lo:hi] if isinstance(v,np.ndarray) else v) for k,v in ask.items()}
        paired,healthy,spread,negative,wide,flatage=quote_quality(qgrid,qsid,b,a)
        status=np.full(len(qgrid),'PAIRED',dtype='<U36')
        status[b['present']&~a['present']]='BID_ONLY_ASK_UNKNOWN'
        status[a['present']&~b['present']]='ASK_ONLY_BID_UNKNOWN'
        status[~b['present']&~a['present']]='BOTH_ABSENT_CAUSE_UNKNOWN'
        extra={'bid_present':b['present'].astype('uint8'),
               'ask_present':a['present'].astype('uint8'),
               'close_spread_bps':np.round(spread,5),
               'negative_close_spread':negative.astype('uint8'),
               'close_spread_gt_50bp':wide.astype('uint8'),
               'joint_flat_age_past_only':flatage,
               'joint_flat_age_ge_15':(flatage>=15).astype('uint8')}
        flags=write_mask(OUT/f'masks_{asset}_PAIRED.csv.gz',qgrid,qsid,dates,paired,healthy,status,
                         np.zeros(len(qgrid),dtype=bool),extra=extra,name=asset+'_PAIRED')
        summary['quotes'][asset]={**flags, 'bid':bid['info'],'ask':ask['info'],
              'bid_only_rth':int((b['present']&~a['present']).sum()),
              'ask_only_rth':int((a['present']&~b['present']).sum()),
              'neither_rth':int((~b['present']&~a['present']).sum()),
              'negative_spread_minutes':int(negative.sum()),
              'close_spread_over_50bp_minutes':int(wide.sum()),
              'joint_flat_past_age_ge15_minutes':int((flatage>=15).sum()),
              'note':'Flat candles may be exporter-synthesized; individual row cause UNCONFIRMED.'}
        del bid,ask,b,a
    summary['classification_rules']={
       'OBSERVED':'An ETF bar exists for that scheduled exchange minute; not certified independent trade accuracy.',
       'LEGACY_ABSENT_UNKNOWN':'No pre-2022 processed ETF bar; cause cannot be recovered from output data.',
       'IEX_RAW_NO_BAR_CAUSE_UNCONFIRMED':'No IEX RAW trade bar; may be no IEX trades, feed gap, or vendor issue.',
       'RAW_PRESENT_OLD_CLEAN_ABSENT':'Old CLEAN has no bar although later RAW does; different release vintage, cause confounded.',
       'NO_RAW_BAR':'Neither compared RAW nor older CLEAN has a recorded bar.',
       'PAIRED':'Both Dukascopy BID and ASK minute candles exist; NOT verified tick freshness.',
       'BID_ONLY_ASK_UNKNOWN':'BID present but ASK missing; not a valid observed two-sided midpoint.',
       'ASK_ONLY_BID_UNKNOWN':'ASK present but BID missing; not a valid observed two-sided midpoint.',
       'BOTH_ABSENT_CAUSE_UNKNOWN':'Neither side recorded during NYSE RTH; may reflect schedule, provider, or export omissions.',
       'known_hf_disruption':'2024-12-23 HF reports IEX truncation; source-wide event flag, not a row-level proven cause.',
       'joint_flat_age_past_only':'Elapsed uninterrupted observed consecutive in-session paired flat OHLC minutes, past-only.',
       'close_spread_gt_50bp':'Diagnostic flag only, not proof of bad quotes or a filtering rule.',
       'missing_run_length':'Retrospective diagnostic run length (uses future to know end); NEVER real-time model feature.',
       'minutes_since_prior_observed':'Past-only distance in scheduled NYSE minutes within session; -1 means no earlier observation.',
    }
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False),encoding='utf-8')
    lines=['# Section 3.3 — Missing-data identification','',
           '**Scope:** categorize what is observed/unobserved; preserve per-minute flags. No imputation, filtering, feature training, or HMM.','',
           '## ETF missingness','',
           '| Dataset | Observed RTH | Absent RTH | Invalid observed OHLC | Missing runs | Longest run |',
           '|---|---:|---:|---:|---:|---:|']
    for key,item in summary['datasets'].items():
        lines.append(f"| {key} | {item['observed']:,} | {item['missing']:,} | {item['invalid_present']:,} | {item['gap_runs']:,} | {item['longest_gap']:,} |")
    lines.extend(['','## Older CLEAN versus later RAW (timestamps only)','',
                  '| Dataset | RAW present, CLEAN absent | Both absent | CLEAN-only |',
                  '|---|---:|---:|---:|'])
    for key,item in summary['comparison'].items():
        lines.append(f"| {key} | {item['raw_present_old_clean_absent']:,} | {item['raw_absent_old_clean_absent']:,} | {item['clean_without_raw']:,} |")
    lines.extend(['','**Caution:** old CLEAN and later RAW archive releases differ; this identifies membership differences, NOT definitive cleaning reasons.','',
                  '## Dukascopy quote availability and suspects','',
                  '| Instrument | Paired | BID only | ASK only | Neither | >50bp spread flag | Past-only joint flat age ≥15m |',
                  '|---|---:|---:|---:|---:|---:|---:|'])
    for key,item in summary['quotes'].items():
        lines.append(f"| {key} | {item['observed']:,} | {item['bid_only_rth']:,} | {item['ask_only_rth']:,} | {item['neither_rth']:,} | {item['close_spread_over_50bp_minutes']:,} | {item['joint_flat_past_age_ge15_minutes']:,} |")
    lines.extend(['','## Interpretation / definite answers','',
       '- **Confirmed:** scheduled closure times are not counted as missing (calendar includes early closes and holidays).',
       '- **Confirmed:** the exact RTH labels and gap lengths for every chosen dataset, with complete CSV masks.',
       '- **Confirmed:** mismatches between RAW and the older CLEAN archive, as distinct vintage comparisons.',
       '- **Confirmed:** quote-sided absence, abnormal close separations, and observed consecutive flat candle streaks.',
       '- **NOT PROVEN:** precise cause of any PiTrading historical missing minute, individual IEX non-trade minute, or quote-server/export omission.',
       '- **NOT PROVEN:** individual flat quote bar synthetic versus genuine stale/unchanged price.',
       '- **NOT TESTED:** impact on actual HMM transitions; requires subsequent feature/model pipeline.',
       '- Retrospective `missing_run_length` is for descriptive work only; it is not legal as a contemporaneous model feature.',
       '- Do not classify all observations during market stress as bad data; Section 3.4/3.5 will choose treatment rules.',
       '', '## Output files','',
       '- `masks_*.csv.gz`: one row per scheduled NYSE minute, with statuses and reproducible flags.',
       '- `gaps_*.csv.gz`: consecutive missing-run ledger without crossing sessions.',
       '- `exchange_sessions.csv`: actual schedule including early closes.',
       '- `summary.json`: exact counts and the data dictionary.',
       '', '## Source preservation','',
       'Input datasets were opened read-only. This script writes only inside Downloads/section3_3_missingness_results.',
       'The original Section 2 file hashes remain the provenance reference.',
       '', '**Next:** review case examples and select handling policies in Sections 3.4/3.5; do not repeat general Section 2 counts.'])
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'\nSUCCESS. Results: {OUT}',flush=True)
    print('Please upload REPORT.md and summary.json first; keep all .csv.gz masks locally.',flush=True)


if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        print(f'\nERROR: {type(exc).__name__}: {exc}',file=sys.stderr)
        raise
