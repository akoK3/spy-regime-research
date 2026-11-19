#!/usr/bin/env python3
"""SECTION 2 — DATA SOURCES & ASSETS: EVIDENCE AUDIT

One reproducible script for the FIVE instruments in the study.
This is a data-audit program, NOT a market-model/HMM or a causal-data-repair script.

INSTALL: python -m pip install pandas numpy pandas_market_calendars
RUN:     python section2_complete_data_audit.py

EDIT 'SOURCES' BELOW to point to your downloaded archives or CSVs.
None means unavailable; script reports a SKIPPED test, never invents a result.
ZIP archives supported: member filename selected by symbol, or specify 'member'.
For each source confirm vendor timezone and candle timestamp convention manually.

REPORTS: section2_audit_results/REPORT.md; summary.json; inventory.csv;
         gaps.csv; daily_coverage.csv; pairwise_overlap.csv;
         source_comparison.csv; findings.csv

This script does NOT and CANNOT:
* prove PiTrading's historical cleaning is/look-ahead-free,
* reconstruct deleted bars, identify whether a missing bar was a zero-trade minute,
* verify historical dividend/split adjustments without independent corporate actions,
* verify dollar-index methodology, supplier licenses, or economic rationale,
* decide optimal HMM features, exclusions, or scientific significance.
It isolates what can be established from the supplied files.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import traceback
import zipfile
from collections import defaultdict
from pathlib import Path

try:
    import numpy as np
    import pandas as pd
    import pandas_market_calendars as mcal
except ImportError as ex:
    raise SystemExit("Install dependencies: python -m pip install pandas numpy pandas_market_calendars") from ex

# ========== USER CONFIGURATION ==============================================
DOWNLOADS = Path.home() / 'Downloads'
RAW_DATA = Path(r'C:\Users\kakij\OneDrive\Desktop\data\raw')
CLEAN_ARCHIVE = DOWNLOADS / 'hfdatalibrary_clean_1min_5tickers_2026-10-03.zip'
OUT = Path(__file__).resolve().parent / 'section2_audit_results'
CUT = pd.Timestamp('2022-03-07 09:30:00')   # source-break first NYSE session
LOCAL_TZ = 'America/New_York'
# Timestamp is the START of the minute by default. If bars stamped by END,
# verify vendor documentation and change 'stamp' to 'end' for that source.
# timezone='America/New_York' for naive local bars; 'UTC' for naive UTC bars.
# If files have tz-aware timestamps, the timezone in the strings is authoritative.
# For Dukascopy BID/ASK, set kind='quotes'. See column normalization below.
# If Dukascopy 'Gmt time' uses DD.MM.YYYY, add dayfirst=True to its dict;
# if parsing still fails, add timestamp_format='%d.%m.%Y %H:%M:%S'.
# Dukascopy can use a merged CSV, or path=BID file plus ask_path=ASK file.
# Separate files are matched by exact timestamp; unmatched sides are reported.
SOURCES = [
    dict(key='SPY_LEGACY', asset='SPY', vendor='HF legacy/PiTrading-processed',
         path=RAW_DATA/'SPY_clean_1min.csv', member=None, kind='ohlcv',
         timezone=LOCAL_TZ, stamp='start', declared_adjustment='UNVERIFIED'),
    dict(key='TLT_LEGACY', asset='TLT', vendor='HF legacy/PiTrading-processed',
         path=RAW_DATA/'TLT_clean_1min.csv', member=None, kind='ohlcv',
         timezone=LOCAL_TZ, stamp='start', declared_adjustment='UNVERIFIED'),
    dict(key='HYG_LEGACY', asset='HYG', vendor='HF legacy/PiTrading-processed',
         path=RAW_DATA/'HYG_clean_1min.csv', member=None, kind='ohlcv',
         timezone=LOCAL_TZ, stamp='start', declared_adjustment='UNVERIFIED'),
    dict(key='SPY_RAW', asset='SPY', vendor='HF IEX RAW',
         path=DOWNLOADS/'hfdatalibrary_raw_1min_1tickers_2026-10-13.zip',
         member='SPY_raw_1min.csv', kind='ohlcv',
         timezone=LOCAL_TZ, stamp='start', declared_adjustment='UNVERIFIED'),
    dict(key='TLT_RAW', asset='TLT', vendor='HF IEX RAW',
         path=RAW_DATA/'hf_raw'/'TLT_raw_1min.csv', member=None, kind='ohlcv', timezone=LOCAL_TZ,
         stamp='start', declared_adjustment='UNVERIFIED'),
    dict(key='HYG_RAW', asset='HYG', vendor='HF IEX RAW',
         path=RAW_DATA/'hf_raw'/'HYG_raw_1min.csv', member=None, kind='ohlcv', timezone=LOCAL_TZ,
         stamp='start', declared_adjustment='UNVERIFIED'),
    # Optional: official modern CLEAN, for exact deletion comparisons
    dict(key='SPY_CLEAN', asset='SPY', vendor='HF IEX CLEAN',
         path=CLEAN_ARCHIVE, member='SPY_clean_1min.csv', kind='ohlcv', timezone=LOCAL_TZ,
         stamp='start', declared_adjustment='UNVERIFIED'),
    dict(key='TLT_CLEAN', asset='TLT', vendor='HF IEX CLEAN',
         path=CLEAN_ARCHIVE, member='TLT_clean_1min.csv', kind='ohlcv', timezone=LOCAL_TZ,
         stamp='start', declared_adjustment='UNVERIFIED'),
    dict(key='HYG_CLEAN', asset='HYG', vendor='HF IEX CLEAN',
         path=CLEAN_ARCHIVE, member='HYG_clean_1min.csv', kind='ohlcv', timezone=LOCAL_TZ,
         stamp='start', declared_adjustment='UNVERIFIED'),
    dict(key='XAUUSD', asset='XAUUSD', vendor='Dukascopy spot-gold bid/ask',
         path=RAW_DATA/'xauusd-m1-bid-2007-04-11-2026-10-02 - Copy.csv',
         ask_path=RAW_DATA/'xauusd-m1-ask-2007-04-11-2026-10-02.csv',
         member=None, kind='quotes', timezone='UTC',
         stamp='start', declared_adjustment='NOT_APPLICABLE'),
    dict(key='DOLLARIDX', asset='DOLLARIDX', vendor='Dukascopy dollaridxusd bid/ask',
         path=RAW_DATA/'dollaridxusd-m1-bid-2017-12-01-2026-10-02.csv',
         ask_path=RAW_DATA/'dollaridxusd-m1-ask-2017-12-01-2026-10-02.csv',
         member=None, kind='quotes', timezone='UTC',
         stamp='start', declared_adjustment='NOT_APPLICABLE'),
]

# Sources are examined only in their declared provenance periods where applicable.
# The calendar grid is built from first through last IN-SESSION data in each file.
# You should cross-check expected availability start dates with vendor documentation.
CANDIDATE_DATES = {
    'SPY': '2002-12-30', 'TLT': '2002-12-30', 'HYG': '2007-04-11',
    'XAUUSD': '2007-04-11', 'DOLLARIDX': '2017-12-01'
}
# Narrow boundary comparison. Seasonality/market volatility can ALSO change.
BREAK_BEFORE_START = '2021-03-07'
BREAK_AFTER_END = '2023-03-06'
EXAMPLE_CRISIS_WINDOWS = {
    'GFC_2008': ('2008-09-01', '2009-03-31'),
    'FLASH_CRASH_2010': ('2010-05-06', '2010-05-06'),
    'COVID_2020': ('2020-02-20', '2020-04-30'),
    '2022_TIGHTENING': ('2022-04-01', '2022-10-31'),
}
# ============================================================================


def val(x):
    """JSON-safe scalar coercion."""
    if isinstance(x, (np.integer,)): return int(x)
    if isinstance(x, (np.floating,)): return float(x) if np.isfinite(x) else None
    if isinstance(x, (pd.Timestamp, pd.Timedelta, Path)): return str(x)
    if isinstance(x, np.bool_): return bool(x)
    if isinstance(x, dict): return {k: val(v) for k, v in x.items()}
    if isinstance(x, (tuple, list)): return [val(y) for y in x]
    if isinstance(x, float) and not np.isfinite(x): return None
    return x


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while True:
            buf=f.read(4*1024*1024)
            if not buf: break
            h.update(buf)
    return h.hexdigest()


def norm(c): return re.sub(r'[^a-z0-9]', '', str(c).lower())


def load_csv_or_zip(spec):
    if spec.get('ask_path') is not None:
        return load_quote_pair(spec)
    path = Path(spec['path'])
    if path.suffix.lower() == '.zip':
        with zipfile.ZipFile(path) as z:
            names=[x for x in z.namelist() if x.lower().endswith('.csv') and not x.endswith('/')]
            if spec.get('member'):
                hit=[n for n in names if n==spec['member'] or n.endswith('/'+spec['member'])]
            else:
                # Refuse guess where multiple symbol matches.
                symbol=spec['asset'].lower()
                hit=[n for n in names if re.search(r'(^|[/_])'+re.escape(symbol)+r'([/_\.]|$)',n.lower())]
            if len(hit)!=1:
                raise ValueError(f"ZIP member ambiguous/unavailable; candidates={hit[:15]}; specify member exactly")
            member=hit[0]
            with z.open(member) as f: df=pd.read_csv(f, low_memory=False)
    elif path.suffix.lower()=='.csv':
        member=None
        df=pd.read_csv(path,low_memory=False)
    elif path.suffix.lower() in ('.parquet','.pq'):
        member=None
        try: df=pd.read_parquet(path)
        except ImportError as e:
            raise RuntimeError('Install pyarrow to read parquet: pip install pyarrow') from e
    else:
        raise ValueError(f'Only CSV, ZIP-of-CSV, and Parquet supported: {path}')
    return df,member


def get_times(df, spec):
    lower={norm(c):c for c in df.columns}
    single=None
    for k in ('datetime','timestamp','datetimeutc','datetimeny','dateandtime','gmttime','utcdate','time'):
        if k in lower:
            single=lower[k]; break
    if single is not None:
        raw=df[single]
        if pd.api.types.is_numeric_dtype(raw) and 'date' not in norm(single):
            median=float(pd.to_numeric(raw,errors='coerce').median())
            unit=('ns' if median>1e17 else 'ms' if median>1e11 else 's')
            series=pd.to_datetime(raw,unit=unit,errors='coerce',utc=True).dt.tz_convert(LOCAL_TZ)
            return series,single
        parsed=pd.to_datetime(raw,errors='coerce',dayfirst=spec.get('dayfirst',False),format=spec.get('timestamp_format'))
        label=single
    elif 'date' in lower and 'time' in lower:
        label=f"{lower['date']} + {lower['time']}"
        parsed=pd.to_datetime(df[lower['date']].astype(str)+' '+df[lower['time']].astype(str),errors='coerce',dayfirst=spec.get('dayfirst',False),format=spec.get('timestamp_format'))
    elif 'date' in lower:
        label=lower['date']
        parsed=pd.to_datetime(df[label], errors='coerce',dayfirst=spec.get('dayfirst',False),format=spec.get('timestamp_format'))
    else:
        raise ValueError(f'Timestamp column not recognized. Columns={list(df.columns)[:30]}')

    if getattr(parsed.dt,'tz',None) is None:
        tz=spec['timezone']
        if not tz: raise ValueError('Naive timestamps require explicit timezone setting.')
        parsed=parsed.dt.tz_localize(tz,ambiguous='NaT',nonexistent='NaT')
    parsed=parsed.dt.tz_convert(LOCAL_TZ)
    if spec['stamp'] == 'end': parsed=parsed-pd.Timedelta(minutes=1)
    elif spec['stamp']!='start':raise ValueError("stamp must be 'start' or 'end'")
    return parsed,label


def match(df, *candidates):
    lookup={norm(c):c for c in df.columns}
    for c in candidates:
        if norm(c) in lookup:return lookup[norm(c)]
    return None


def load_quote_pair(spec):
    """Join original BID/ASK files without filling or shifting observations."""
    frames = []
    members = []
    for side, path, member in (
        ('Bid', spec['path'], spec.get('member')),
        ('Ask', spec['ask_path'], spec.get('ask_member')),
    ):
        side_spec = dict(spec, path=path, member=member, ask_path=None)
        raw, selected_member = load_csv_or_zip(side_spec)
        times, _ = get_times(raw, side_spec)
        if times.isna().any():
            raise ValueError(f'{side} file has {int(times.isna().sum())} invalid timestamps: {path}')
        if times.duplicated().any():
            raise ValueError(f'{side} file has duplicate timestamps; cannot pair quotes one-to-one: {path}')
        frame = pd.DataFrame({'datetime': times})
        for col in ('Open', 'High', 'Low', 'Close'):
            source = match(raw, col, 'price'+col, side+col, col+side)
            if source is None:
                raise ValueError(f'{side} {col} absent in {path}')
            frame[side+col] = pd.to_numeric(raw[source], errors='coerce')
        frames.append(frame)
        members.append(selected_member)
    bid, ask = frames
    paired = bid.merge(ask, on='datetime', how='inner', validate='one_to_one', sort=False)
    paired.attrs['quote_pair'] = {
        'bid_file': str(spec['path']), 'ask_file': str(spec['ask_path']),
        'bid_zip_member': members[0], 'ask_zip_member': members[1],
        'bid_rows': len(bid), 'ask_rows': len(ask), 'paired_rows': len(paired),
        'bid_only_timestamps': len(bid)-len(paired),
        'ask_only_timestamps': len(ask)-len(paired),
        'alignment': 'Exact timestamp intersection; no quote filling',
    }
    return paired, members[0]


def extract_prices(df,spec):
    kind=spec['kind']
    data={}
    for col in ('Open','High','Low','Close'):
        if kind=='ohlcv':
            c=match(df,col,'price'+col)
            if c is None: raise ValueError(f'{col} absent in {list(df.columns)}')
            data[col]=pd.to_numeric(df[c],errors='coerce')
        else:
            for side in ('Bid','Ask'):
                # Examples: BidOpen, bid_open, open_bid, BID_OPEN, <BIDOPEN>
                c=match(df,side+col,col+side,side+'Price'+col)
                if c is None:
                    if col!='Close': continue
                    raise ValueError(f'Cannot identify {side}{col} quote fields; found {list(df.columns)[:40]}')
                data[side+col]=pd.to_numeric(df[c],errors='coerce')
    if kind=='ohlcv':
        vc=match(df,'Volume','Vol','TickVolume')
        if vc is not None:data['Volume']=pd.to_numeric(df[vc],errors='coerce')
    else:
        data['Close']=(data['BidClose']+data['AskClose'])/2
        data['Spread']=data['AskClose']-data['BidClose']
        data['SpreadBps']=10000*data['Spread']/data['Close']
        for col in ('Open','High','Low'):
            if 'Bid'+col in data and 'Ask'+col in data:
                data[col]=(data['Bid'+col]+data['Ask'+col])/2
    sourcec=match(df,'source','exchange','feed')
    if sourcec is not None:data['source_tag']=df[sourcec].astype('string')
    return pd.DataFrame(data)


def ingest(spec):
    raw,member=load_csv_or_zip(spec)
    times,timecol=get_times(raw,spec)
    prices=extract_prices(raw,spec)
    prices['ts']=times
    # Input source record QA before dropping any rows
    malformed=int(prices['ts'].isna().sum())
    dup=int(prices['ts'].duplicated(keep=False).sum())
    dup_exact=int(prices.duplicated().sum())
    numeric_cols=[x for x in prices.columns if x not in ('ts','source_tag')]
    nonfinite={c:int((~np.isfinite(prices[c].to_numpy(dtype='float64'))).sum()) for c in numeric_cols}
    positive=[c for c in numeric_cols if any(w in c for w in ('Open','High','Low','Close'))]
    nonpositive={c:int((prices[c]<=0).sum()) for c in positive}
    geometry={}
    if all(c in prices.columns for c in ('Open','High','Low','Close')):
        high,low,o,c=[prices[s] for s in ('High','Low','Open','Close')]
        geometry['bad_midpoint_OHLC'] = int(((low>high)|(o>high)|(o<low)|(c>high)|(c<low)).sum())
    for side in ('Bid','Ask'):
        cols=[side+x for x in ('Open','High','Low','Close')]
        if all(c in prices.columns for c in cols):
            o,h,l,c=[prices[x] for x in cols]
            geometry['bad_'+side+'_OHLC']=int(((l>h)|(o>h)|(o<l)|(c>h)|(c<l)).sum())
    if 'Volume' in prices:
        geometry['negative_volume']=int((prices['Volume']<0).sum())
        geometry['zero_volume']=int((prices['Volume']==0).sum())
    if 'Spread' in prices:
        geometry['negative_bid_ask_close_spread']=int((prices['Spread']<0).sum())
        geometry['zero_spread']=int((prices['Spread']==0).sum())
    prices=prices.dropna(subset=['ts']).sort_values('ts',kind='stable')
    # No silent duplicate resolution: flag and retain first ONLY for diagnostics.
    prices_unique=prices.drop_duplicates(subset=['ts'],keep='first').set_index('ts')
    prices_unique.index=pd.DatetimeIndex(prices_unique.index)
    summary={
        'file':str(spec['path']), 'zip_member':member,
        'rows_original':len(raw), 'rows_valid_timestamp':len(prices),
        'rows_unique_timestamp':len(prices_unique), 'malformed_timestamps':malformed,
        'duplicate_timestamp_rows':dup,'exact_duplicate_rows':dup_exact,
        'source_datetime_column':timecol,'input_columns':list(raw.columns),
        'numeric_not_finite':nonfinite,'nonpositive_prices':nonpositive,
        **geometry,
        'first':str(prices_unique.index.min()) if len(prices_unique) else None,
        'last':str(prices_unique.index.max()) if len(prices_unique) else None,
        'reported_source_values':prices_unique['source_tag'].value_counts(dropna=False).head(10).to_dict()
            if 'source_tag' in prices_unique else {},
        'timestamp_timezone_assumed':spec['timezone'],
        'candle_timestamp_position_assumed':spec['stamp'],
        'price_adjustment_status':spec['declared_adjustment'],
        'date_range_count':len(prices_unique.index.normalize().unique()),
        'timestamps_not_exact_minute':int(((prices_unique.index.second!=0)|(prices_unique.index.microsecond!=0)).sum()),
        'declared_vendor_frequency':'1-minute, verify with vendor',
    }
    if 'quote_pair' in raw.attrs:
        summary['quote_pair'] = raw.attrs['quote_pair']
    return prices_unique, val(summary)


nyse = mcal.get_calendar('NYSE')
_calendar_cache={}
def get_calendar(start,end):
    key=(pd.Timestamp(start).date(),pd.Timestamp(end).date())
    if key not in _calendar_cache:
        sched=nyse.schedule(start_date=key[0],end_date=key[1])
        _calendar_cache[key]=sched
    return _calendar_cache[key]


def session_grid(start,end):
    sch=get_calendar(start,end)
    chunks=[]
    for _,s in sch.iterrows():
        opening=s['market_open'].tz_convert(LOCAL_TZ)
        closing=s['market_close'].tz_convert(LOCAL_TZ)
        if closing>opening:
            chunks.append(pd.date_range(opening,closing-pd.Timedelta(minutes=1),freq='min'))
    if not chunks:return pd.DatetimeIndex([],tz=LOCAL_TZ)
    # Handles DST correctly in aware NY timestamps.
    return chunks[0].append(chunks[1:]) if len(chunks)>1 else chunks[0]


def classify_by_session(data):
    if data.empty:return {'rth':0,'outside_rth':0}
    idx=session_grid(data.index.min(),data.index.max())
    inrth=data.index.isin(idx)
    raw_oob=data.index[~inrth]
    overnight=raw_oob[(raw_oob.hour<9)|(raw_oob.hour>=16)]
    return {'rth':int(inrth.sum()),'outside_rth':int((~inrth).sum()),
            'outside_rth_overnight':int(len(overnight)),
            'examples_outside_rth':[str(x) for x in raw_oob[:6]]}


def coverage(data,key):
    if data.empty:return {},pd.DataFrame(),pd.DataFrame(),None
    inbounds=data.index
    grid=session_grid(inbounds.min(),inbounds.max())
    # Restrict to actual first/last observed timestamp; avoid partial first/last artifact.
    grid=grid[(grid>=inbounds.min())&(grid<=inbounds.max())]
    observed=pd.Series(False,index=grid)
    common=grid.intersection(inbounds)
    observed.loc[common]=True
    missing=~observed
    session_day=pd.Series(grid.date,index=grid)
    # Overnight/weekend boundaries are not a single contiguous missing run.
    group_starts=missing.ne(missing.shift()) | session_day.ne(session_day.shift())
    g=missing.groupby(group_starts.cumsum())
    gap_rows=[]
    for _,block in g:
        if not block.iloc[0]:continue
        gap_rows.append({'key':key,'start':block.index[0], 'end':block.index[-1],
                         'length':int(len(block)),'session_date':str(block.index[0].date())})
    gapdf=pd.DataFrame(gap_rows)
    by_day=observed.groupby(observed.index.date).agg(['sum','size'])
    by_day.columns=['observed','expected']
    by_day['missing']=by_day['expected']-by_day['observed']
    by_day['coverage_pct']=100*by_day['observed']/by_day['expected']
    by_day=by_day.reset_index(names='session_date');by_day.insert(0,'key',key)
    years=by_day.groupby(pd.to_datetime(by_day['session_date']).dt.year)[['observed','expected','missing']].sum()
    years['coverage_pct']=100*years['observed']/years['expected']
    years=years.reset_index(names='year'); years.insert(0,'key',key)
    day_summary={'expected_rth_minutes':len(grid),'observed_rth_minutes':len(common),
                 'missing_rth_minutes':int(missing.sum()),
                 'coverage_pct':float(100*observed.mean()),
                 'sessions':len(by_day),
                 'gaps':len(gapdf),
                 'single_minute_gap_fraction':float((gapdf['length']==1).mean()) if len(gapdf) else 0,
                 'gaps_2_to_5':int(gapdf['length'].between(2,5).sum()) if len(gapdf) else 0,
                 'gaps_over_5':int((gapdf['length']>5).sum()) if len(gapdf) else 0,
                 'longest_gap_minutes':int(gapdf['length'].max()) if len(gapdf) else 0}
    return day_summary, by_day, years, (grid,observed,gapdf)


def quote_stats(data):
    if 'SpreadBps' not in data:return None
    raw=data['SpreadBps'].replace([np.inf,-np.inf],np.nan).dropna()
    close=data['Close']
    rth=data.index.isin(session_grid(data.index.min(),data.index.max()))
    z=data.loc[rth, 'SpreadBps'].dropna()
    diff=pd.to_numeric(close,errors='coerce').diff()
    # consecutive clocks only; zero-change is a STALENESS INDICATOR, not proof.
    valid=(data.index.to_series().diff()==pd.Timedelta(minutes=1))
    flat=(diff.eq(0)&valid)
    return {'rows':len(data),'spread_bps_median':float(raw.median()) if len(raw) else None,
            'spread_bps_p95':float(raw.quantile(.95)) if len(raw) else None,
            'spread_bps_p99':float(raw.quantile(.99)) if len(raw) else None,
            'spread_bps_max':float(raw.max()) if len(raw) else None,
            'rth_spread_bps_median':float(z.median()) if len(z) else None,
            'negative_close_spreads':int((raw<0).sum()),
            'consecutive_unchanged_close_fraction':float(flat.sum()/valid.sum()) if valid.sum() else None,
            'note':'Zero midpoint changes suggest possible quote staleness; does not prove it.'}


def compare_raw_clean(raw,clean,key):
    # Different download dates must not turn later RAW sessions into deletions.
    start=max(raw.index.min(), clean.index.min())
    end=min(raw.index.max(), clean.index.max())
    if start>end:
        raise ValueError(f'{key}: RAW and CLEAN have no overlapping timestamps')
    raw_full_rows=len(raw); clean_full_rows=len(clean)
    raw=raw.loc[(raw.index>=start)&(raw.index<=end)]
    clean=clean.loc[(clean.index>=start)&(clean.index<=end)]
    x=raw.index.intersection(clean.index)
    removed=raw.index.difference(clean.index)
    added=clean.index.difference(raw.index)
    deltas=pd.DataFrame(index=x)
    for col in ['Open','High','Low','Close','Volume']:
        if col in raw and col in clean:
            a=raw.loc[x,col].astype(float);b=clean.loc[x,col].astype(float)
            deltas[col]=(a-b).abs()>np.maximum(1e-8,1e-9*a.abs())
    return {'key':key,'raw_rows':len(raw),'clean_rows':len(clean),
            'comparison_start':str(start),'comparison_end':str(end),
            'raw_rows_outside_comparison':raw_full_rows-len(raw),
            'clean_rows_outside_comparison':clean_full_rows-len(clean),
            'removed_timestamps':len(removed), 'added_timestamps':len(added),
            'removed_fraction_raw_pct':100*len(removed)/len(raw),
            'overlapping_timestamps':len(x),
            'overlap_changed_fraction_by_column_pct':{
                c:float(100*deltas[c].mean()) for c in deltas.columns},
            'first_removed_examples':[str(y) for y in removed[:6]]}


def coincidence(a,b,name1,name2):
    start=max(a[0].min(),b[0].min());end=min(a[0].max(),b[0].max())
    if start>end:return None
    x=a[1][(a[1].index>=start)&(a[1].index<=end)]
    y=b[1][(b[1].index>=start)&(b[1].index<=end)]
    g=x.index.intersection(y.index)
    aa=~x.loc[g];bb=~y.loc[g]
    both=int((aa&bb).sum());union=int((aa|bb).sum())
    expected=len(g)*aa.mean()*bb.mean()
    return {'pair':f'{name1}–{name2}','common_expected_minutes':len(g),
            'missing_a':int(aa.sum()),'missing_b':int(bb.sum()),
            'both_missing':both,'jaccard_missing':float(both/union) if union else None,
            'both_missing_expected_if_independent':float(expected),
            'obs_to_independent_ratio':float(both/expected) if expected else None,
            'WARNING':'Shared gaps can also represent market halts, trading pauses, or common infrastructure—not proof of identical cleaning.'}


def pairwise_metrics(grida,gridb,asset_a,asset_b):
    lo=max(grida.index.min(),gridb.index.min());hi=min(grida.index.max(),gridb.index.max())
    if lo>hi:return None
    common=grida.index.intersection(gridb.index)
    common=common[(common>=lo)&(common<=hi)]
    both=int((grida.reindex(common,fill_value=False)&gridb.reindex(common,fill_value=False)).sum())
    return {'trigger':asset_a,'response':asset_b,'overlap_start':str(lo),
            'overlap_end':str(hi),'expected_synchronized_minutes':len(common),
            'minutes_both_observed':both,
            'both_coverage_pct':100*both/len(common) if len(common) else None,
            'note':'Timestamp intersection only; final event-window eligibility deferred to later sections.'}


def gap_events(gapdf,meta_key):
    out=[]
    for name,(first,last) in EXAMPLE_CRISIS_WINDOWS.items():
        if gapdf.empty:continue
        a=pd.Timestamp(first).date();b=pd.Timestamp(last).date()
        x=gapdf[(pd.to_datetime(gapdf['session_date']).dt.date>=a)&
                (pd.to_datetime(gapdf['session_date']).dt.date<=b)]
        out.append({'key':meta_key,'event':name,'gap_runs':len(x),'missing_minutes':int(x['length'].sum())})
    return out


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    manifest=[]; findings=[]; loaderrors=[]; all_data={}; covered={}; grids={}
    gaps=[]; daily=[]; annual=[]; all_quotes=[]; crises=[]; rows_source=[]
    def finding(section,item,status,evidence):
        findings.append({'section':section,'question':item,'status':status,'evidence':str(evidence)})
    # record dependency versions
    software={'python':__import__('sys').version,'pandas':pd.__version__,
              'numpy':np.__version__,'pandas_market_calendars':getattr(mcal,'__version__','unknown')}

    for s in SOURCES:
        key=s['key'];p=s.get('path');print('Source:',key)
        absent=[str(q) for q in (p,s.get('ask_path')) if q is not None and not Path(q).is_file()]
        if p is None or absent:
            msg='Not configured' if p is None else 'File absent: '+', '.join(absent)
            loaderrors.append({'key':key,'status':'SKIPPED','reason':msg})
            print('   SKIPPED —',msg)
            continue
        try:
            meta={'key':key,'asset':s['asset'],'vendor':s['vendor'],
                  'filename':str(p),'bytes':Path(p).stat().st_size,
                  'sha256':sha256(p),'kind':s['kind'],
                  'timezone_setting':s['timezone'],'stamp_setting':s['stamp'],
                  'declared_adjustment':s['declared_adjustment']}
            data,quality=ingest(s)
            if data.empty:raise ValueError('No parsed timestamps available')
            # Archives also contain the other provenance period; audit each separately.
            cut=CUT.tz_localize(LOCAL_TZ)
            if key.endswith('_LEGACY'):
                data=data.loc[data.index<cut]
            elif key.endswith(('_RAW','_CLEAN')):
                data=data.loc[data.index>=cut]
            if data.empty:raise ValueError('No timestamps in the declared source period')
            quality.update({'rows_in_source_period':len(data),
                            'source_period_first':str(data.index.min()),
                            'source_period_last':str(data.index.max())})
            meta.update(quality)
            if s.get('ask_path') is not None:
                meta.update({'ask_filename':str(s['ask_path']),
                             'ask_bytes':Path(s['ask_path']).stat().st_size,
                             'ask_sha256':sha256(s['ask_path'])})
                ask_member=quality.get('quote_pair',{}).get('ask_zip_member')
                if ask_member and Path(s['ask_path']).suffix.lower()=='.zip':
                    h=hashlib.sha256()
                    with zipfile.ZipFile(s['ask_path']) as archive, archive.open(ask_member) as stream:
                        for buf in iter(lambda:stream.read(4*1024*1024),b''):
                            h.update(buf)
                    meta['ask_zip_member_sha256']=h.hexdigest()
            all_data[key]=data
            sess=classify_by_session(data)
            for col,v in sess.items():meta['session_'+col]=v
            # Archive member checksum permits file-specific reproducibility.
            if meta.get('zip_member') and Path(p).suffix.lower()=='.zip':
                h=hashlib.sha256()
                with zipfile.ZipFile(p).open(meta['zip_member']) as stream:
                    while True:
                        buf=stream.read(4*1024*1024)
                        if not buf: break
                        h.update(buf)
                meta['zip_member_sha256']=h.hexdigest()
            manifest.append(val(meta))
            cov,day,year,grid=coverage(data,key)
            covered[key]=val(cov)
            if grid is not None:
                idx,observed,missing_runs=grid;grids[key]=(idx,observed)
                if len(missing_runs):
                    gaps.append(missing_runs)
                    crises.extend(gap_events(missing_runs,key))
            if len(day):daily.append(day)
            if len(year):annual.append(year)
            qs=quote_stats(data)
            if qs:all_quotes.append({'key':key,**qs})
            finding('2.3',f'{key} data-read and integrity', 'REQUIRES_REVIEW' if quality['duplicate_timestamp_rows'] or quality['malformed_timestamps'] else 'MEASURED',
                    f"{quality['rows_original']} rows; {cov['coverage_pct']:.3f}% RTH coverage; SHA256 saved")
            print('   rows:',len(data),'RTH coverage:',round(cov['coverage_pct'],3),'%')
        except Exception as e:
            loaderrors.append({'key':key,'status':'FAILED','reason':str(e)})
            print('   ERROR:',str(e))
            traceback.print_exc(limit=1)

    # First match legacy and modern, avoid accidentally joining gaps across the source break.
    def assembled(asset):
        pieces=[]
        for suffix in ['LEGACY','RAW']:
            k=f'{asset}_{suffix}'
            if k not in all_data:continue
            x=all_data[k]
            cut=CUT.tz_localize(LOCAL_TZ)
            pieces.append(x[x.index<cut] if suffix=='LEGACY' else x[x.index>=cut])
        if not pieces:return None
        x=pd.concat(pieces).sort_index()
        return x[~x.index.duplicated(keep='first')]
    master={a:(assembled(a) if a in ('SPY','TLT','HYG') else all_data.get(a))
            for a in ['SPY','TLT','HYG','XAUUSD','DOLLARIDX']}
    mgrid={}
    for a,x in master.items():
        if x is None or x.empty:continue
        idx=session_grid(x.index.min(),x.index.max())
        idx=idx[(idx>=x.index.min())&(idx<=x.index.max())]
        obs=pd.Series(idx.isin(x.index),index=idx)
        mgrid[a]=obs

    pairwise=[]
    for response in ['TLT','HYG','XAUUSD','DOLLARIDX']:
        if 'SPY' in mgrid and response in mgrid:
            metric=pairwise_metrics(mgrid['SPY'],mgrid[response],'SPY',response)
            if metric:pairwise.append(metric)

    common=None
    if len(mgrid)==5:
        start=max(x.index.min() for x in mgrid.values())
        end=min(x.index.max() for x in mgrid.values())
        if start<=end:
            idx=session_grid(start,end)
            idx=idx[(idx>=start)&(idx<=end)]
            flags=[x.reindex(idx,fill_value=False) for x in mgrid.values()]
            both=flags[0].copy()
            for f in flags[1:]:both=both&f
            common={'period_start':str(start),'period_end':str(end),
                    'expected_common_minutes':len(idx),
                    'minutes_all_five_observed':int(both.sum()),
                    'complete_minute_coverage_pct':float(100*both.mean()) if len(idx) else 0}

    coincidences=[]
    for a,b in [('SPY_LEGACY','TLT_LEGACY'),('SPY_LEGACY','HYG_LEGACY'),
                ('TLT_LEGACY','HYG_LEGACY')]:
        if a in grids and b in grids:
            co=coincidence(grids[a],grids[b],a,b)
            if co:coincidences.append(co)

    exact=[]
    for asset in ['SPY','TLT','HYG']:
        a=asset+'_RAW';b=asset+'_CLEAN'
        if a in all_data and b in all_data:
            exact.append(compare_raw_clean(all_data[a],all_data[b],asset))

    discontinuity=[]
    for asset in ['SPY','TLT','HYG']:
        a=asset+'_LEGACY';b=asset+'_RAW'
        if a not in all_data or b not in all_data:continue
        q1=all_data[a];q2=all_data[b]
        z1=q1[(q1.index>=pd.Timestamp(BREAK_BEFORE_START,tz=LOCAL_TZ))&(q1.index<CUT.tz_localize(LOCAL_TZ))]
        z2=q2[(q2.index>=CUT.tz_localize(LOCAL_TZ))&(q2.index<=pd.Timestamp(BREAK_AFTER_END+' 23:59',tz=LOCAL_TZ))]
        for label,z in [('legacy_pre12m',z1),('IEX_RAW_post12m',z2)]:
            if z.empty:continue
            g,_,_,_=coverage(z,label)
            records={'asset':asset,'period':label,**g}
            # no claims that volatility change was caused by the vendor alone
            adj=z['Close'].pct_change()
            consecutive=z.index.to_series().diff().eq(pd.Timedelta(minutes=1))
            ret=adj[consecutive]
            records.update({'abs_1m_return_q99':float(ret.abs().quantile(.99)),
                            'abs_1m_return_q999':float(ret.abs().quantile(.999))})
            if 'Volume' in z:
                v=z['Volume'].dropna()
                records.update({'volume_median':float(v.median()) if len(v) else None,
                                'volume_q95':float(v.quantile(.95)) if len(v) else None})
            discontinuity.append(records)

    # Descriptive time profile: use missing minutes, which may be zero-trade minutes.
    timeprofiles=[]
    for key,(_,observed) in grids.items():
        idx=observed.index[~observed]
        if not len(idx):continue
        mins=(idx.hour*60+idx.minute)-(9*60+30)
        buckets={'first30':(0,30),'30to120':(30,120),'midday':(120,300),'last90':(300,390)}
        d={'key':key,'missing_total':len(idx)}
        for name,(lo,hi) in buckets.items():
            d[name+'_pct']=100*float(((mins>=lo)&(mins<hi)).mean())
        timeprofiles.append(d)

    # Important: a source metadata absence is not a proven problem with its vendor.
    for a in ['SPY','TLT','HYG','XAUUSD','DOLLARIDX']:
        status='MEASURED' if a in mgrid else 'NOT_RUN'
        finding('2.1',a+' actual historical coverage',status,
                f"Observed {int(mgrid[a].sum())}/{len(mgrid[a])} RTH minutes" if a in mgrid else 'Provide its source paths.')
    finding('2.3','PiTrading centered versus causal historical filter','NOT_DECIDABLE',
            'Missing legacy RAW trade data: gap shapes alone cannot prove use of future information.')
    finding('2.3','Post-2022 official RAW versus CLEAN deletion counts',
            'MEASURED' if exact else 'NOT_RUN','Exact timestamp comparison only when both archives supplied.')
    finding('2.3','Provider feed and consolidated versus IEX history','NEEDS_VENDOR_DOCUMENTATION',
            'Source-tag and source break can be inspected; full exchange coverage cannot be established from OHLCV alone.')
    finding('2.3','Dividend/split adjustment as-of conventions','NEEDS_VENDOR_DOCUMENTATION',
            'Cannot verify adjustment policy from OHLCV alone. Need corporate action documentation and comparison files.')
    finding('2.4','Candle timestamps represent bar open or end','NEEDS_VENDOR_DOCUMENTATION',
            'Settings are explicit but cannot be identified with certainty from 1-minute bars alone.')
    finding('2.4','Dukascopy dollar index equals ICE DXY','NEEDS_VENDOR_DOCUMENTATION',
            'These are NOT automatically equivalent; verify underlying instrument definition.')
    finding('2.5','Five-asset common-window completeness',
            'MEASURED' if common else 'NOT_RUN',common if common else 'Supply all required datasets.')
    finding('2.5','Definitive event-window gap exclusions','DEFER_TO_PREPROCESSING',
            'Define thresholds and test after raw data source audit.')
    finding('2.2','Economic rationale/liquidity and instrument selection','REQUIRES_EXTERNAL_REFERENCES',
            'Coverage does not establish economic validity or microstructure comparability.')

    results={'metadata':software,'manifest':manifest,'load_problems':loaderrors,
             'source_coverage':covered,'pairwise_overlap':pairwise,
             'common_5_asset_window':common,'cross_asset_gap_coincidence':coincidences,
             'raw_vs_official_clean':exact,'march_2022_discontinuity':discontinuity,
             'quote_quality':all_quotes,'time_of_day_missingness':timeprofiles,
             'crisis_missingness':crises,'decision_status':findings}
    (OUT/'summary.json').write_text(json.dumps(val(results),indent=2,ensure_ascii=False,default=str),encoding='utf-8')
    def dump(df,name):
        if df is not None and len(df):pd.DataFrame(df).to_csv(OUT/name,index=False)
    dump(manifest,'inventory.csv')
    dump(findings,'findings.csv')
    dump(pairwise,'pairwise_overlap.csv')
    dump(discontinuity,'source_comparison.csv')
    dump(all_quotes,'quotes.csv')
    dump(timeprofiles,'time_of_day.csv')
    dump(coincidences,'synchronized_gaps.csv')
    dump(exact,'raw_vs_clean.csv')
    dump(crises,'crisis_gaps.csv')
    if gaps:pd.concat(gaps,ignore_index=True).to_csv(OUT/'gaps.csv',index=False)
    if daily:pd.concat(daily,ignore_index=True).to_csv(OUT/'daily_coverage.csv',index=False)
    if annual:pd.concat(annual,ignore_index=True).to_csv(OUT/'annual_coverage.csv',index=False)

    lines=['# Section 2: Data source audit','',
           '**Evidence report only.** Missing observations can reflect no trade, data outages, halts, or filtering. '
           'No conclusion about pre-2022 look-ahead is possible from gap shapes alone.','',
           '## Files processed']
    for s in SOURCES:
        k=s['key'];p=s.get('path')
        status=('LOADED' if k in all_data else 'NOT LOADED')
        inputs=str(p or 'not configured')
        if s.get('ask_path') is not None:inputs+=' + ASK '+str(s['ask_path'])
        lines.append(f'- {k}: {status} — {inputs}')
    lines+=['','## 2.1/2.3. File provenance & observed RTH coverage','']
    for s in SOURCES:
        k=s['key']
        if k not in all_data:continue
        c=covered[k]
        lines.append(f'- **{k}:** {c["coverage_pct"]:.3f}% RTH-minute coverage; '
                     f'{c["observed_rth_minutes"]:,} observed of {c["expected_rth_minutes"]:,} expected; '
                     f'{c["missing_rth_minutes"]:,} absent; {c["gaps"]:,} missing runs')
    lines+=['','## 2.4/2.5. SPY versus response overlap','']
    for x in pairwise:
        lines.append(f'- SPY → {x["response"]}: {x["overlap_start"]} to {x["overlap_end"]}; '
                     f'{x["minutes_both_observed"]:,} / {x["expected_synchronized_minutes"]:,} synchronous '
                     f'RTH minutes ({x["both_coverage_pct"]:.3f}%)')
    if common:
        lines.append(f'- **All five:** {common["complete_minute_coverage_pct"]:.3f}% complete '
                     f'in {common["period_start"]}–{common["period_end"]}')
    else:lines.append('- All-five overlap: NOT MEASURABLE with current configured files.')
    lines+=['','## 2.3. Historical provenance and source discontinuity','']
    if discontinuity:
        for x in discontinuity:
            lines.append(f'- {x["asset"]} {x["period"]}: coverage {x["coverage_pct"]:.3f}%; '
                         f'99th percentile absolute 1-minute returns {x["abs_1m_return_q99"]:.6g}')
    else: lines.append('Missing legacy-modern pairs; cannot calculate discontinuity.')
    if exact:
        for x in exact:
            lines.append(f'- **{x["key"]}:** within {x["comparison_start"]} to {x["comparison_end"]}, '
                         f'official CLEAN lacks {x["removed_timestamps"]:,} RAW timestamps '
                         f'({x["removed_fraction_raw_pct"]:.3f}%); '
                         f'{x["raw_rows_outside_comparison"]:,} RAW rows outside the shared period were excluded.')
    else:lines.append('Official RAW versus CLEAN exact comparison: NOT RUN.')
    lines+=['','## 2.3. Legacy synchronized gaps','']
    for x in coincidences:
        lines.append(f'- {x["pair"]}: {x["both_missing"]:,} identical missing timestamps; '
                     f'Jaccard {x["jaccard_missing"]:.3f}; this does **not** prove common filtering.')
    if not coincidences:lines.append('Not run: requires at least two legacy ETF datasets.')
    lines+=['','## 2.3. Dukascopy quote quality','']
    for x in all_quotes:
        lines.append(f'- {x["key"]}: median close spread {x["spread_bps_median"]:.3f} basis points; '
                     f'p99 {x["spread_bps_p99"]:.3f}; negative spreads {x["negative_close_spreads"]:,}.')
    if not all_quotes:lines.append('Not run: configure Dukascopy files and column mapping.')
    lines+=['','## Decisions still requiring evidence','']
    for x in findings:
        if x['status'] not in ('MEASURED',):
            lines.append(f'- **{x["status"]}** {x["question"]}: {x["evidence"]}')
    lines+=['','## Interpreting this report',
            '- A 1-minute master grid is a reproducible reference, not a promise that all markets trade every minute.',
            '- FX quote MIDPOINT is not a traded execution price. Unlike ETF trade prints, quotes may remain stale.',
            '- A price/volume distribution break in 2022 can reflect market conditions as well as the vendor change.',
            '- Missing bar patterns cannot identify exactly which historical algorithm PiTrading used.',
            '- Do not use this script to select HMM parameters or tune outcomes.',
            '- Final gap-handling rules, HMM leakage controls, event completeness, and robustness belong in Sections 3 onward.',
            '','See **summary.json** and per-test CSVs for exact numbers.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'+'='*66)
    print('SECTION 2 COMPLETE — AUDIT FINISHED, NOT ALL ISSUES RESOLVED')
    print('Loaded',len(all_data),'of',len(SOURCES),'sources; errors/skips',len(loaderrors))
    print('Files:',OUT.resolve())
    print('Share REPORT.md or summary.json for a rigorous decision-by-decision review.')


if __name__=='__main__':
    main()
