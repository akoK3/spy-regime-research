#!/usr/bin/env python3
"""Section 3.2 quote-alignment correction, read-only source data.

Fixes a verified pandas unit mismatch in the prior audit: timestamp input in
milliseconds remained datetime64[ms] and was compared to a nanosecond NYSE grid.
This script reuses the completed ETF summary, reads only four Dukascopy files
and two SPY timestamp columns, and writes NEW, explicitly corrected outputs.

Requirements: pandas, numpy, pandas_market_calendars
Run: python "$HOME\\Downloads\\section3_2_quote_alignment_fix.py"
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

HOME=Path.home()
RAW=HOME/'OneDrive'/'Desktop'/'data'/'raw'
DL=HOME/'Downloads'
OUT=DL/'section3_2_timestamp_results'
MINUTE_NS=60_000_000_000
CHUNK=450_000
QUOTES={
    'GOLD_BID': RAW/'xauusd-m1-bid-2007-04-11-2026-10-02 - Copy.csv',
    'GOLD_ASK': RAW/'xauusd-m1-ask-2007-04-11-2026-10-02.csv',
    'DOLLAR_BID': RAW/'dollaridxusd-m1-bid-2017-12-01-2026-10-02.csv',
    'DOLLAR_ASK': RAW/'dollaridxusd-m1-ask-2017-12-01-2026-10-02.csv',
}


def assert_timestamp_conversion():
    """Regression test: epoch milliseconds become epoch NANOseconds."""
    known=pd.Timestamp('2024-03-11 13:30:00',tz='UTC')
    ms=known.value//1_000_000
    s=pd.Series([str(ms)],dtype='string')
    converted=pd.to_datetime(pd.to_numeric(s),unit='ms',utc=True).dt.as_unit('ns').astype('int64').iloc[0]
    assert int(converted)==int(known.value), f'Millisecond-to-nanosecond conversion FAILED: {converted} != {known.value}'
    print('PASS: timestamp unit regression test (ms -> ns)', flush=True)


def build_grid():
    try:
        import pandas_market_calendars as pmc
        sch=pmc.get_calendar('XNYS').schedule(start_date='2002-12-30',end_date='2026-10-14')
        opens=sch['market_open'].astype('int64').to_numpy(dtype=np.int64)
        closes=sch['market_close'].astype('int64').to_numpy(dtype=np.int64)
    except ImportError:
        import exchange_calendars as ec
        sch=ec.get_calendar('XNYS',start='2002-12-30',end='2026-10-14').schedule
        opens=sch['open'].astype('int64').to_numpy(dtype=np.int64)
        closes=sch['close'].astype('int64').to_numpy(dtype=np.int64)
    grid=np.concatenate([np.arange(x,y,MINUTE_NS,dtype=np.int64) for x,y in zip(opens,closes)])
    assert len(grid)>2_000_000
    print(f'Exchange calendar: {len(grid):,} scheduled minute starts (UTC nanoseconds)',flush=True)
    return grid


def quote_ts(path, grid):
    if not path.is_file(): raise FileNotFoundError(f'Missing source file: {path}')
    header=pd.read_csv(path,nrows=0)
    col=next((c for c in header.columns if c.strip().lower() in ('timestamp','datetime','time')),None)
    if col is None: raise ValueError(f'No timestamp column in {path}: {list(header.columns)}')
    chunks=[]; total=0; bad=0; min_time=None; max_time=None
    for df in pd.read_csv(path,usecols=[col],dtype='string',chunksize=CHUNK):
        series=df[col].str.strip()
        nonnull=series.dropna()
        if len(nonnull)==0: continue
        probe=nonnull.iloc[0]
        if not probe.lstrip('+-').isdigit():
            raise ValueError(f'Expected numeric Unix timestamp in {path}, got {probe!r}')
        magnitude=len(probe.lstrip('+-'))
        unit='ms' if magnitude in (12,13) else ('s' if magnitude in (9,10) else ('us' if magnitude in (15,16) else 'ns'))
        ts=pd.to_datetime(pd.to_numeric(series,errors='coerce'),unit=unit,utc=True,errors='coerce')
        bad+=int(ts.isna().sum())
        ts=ts.dropna()
        if ts.empty: continue
        # IMPORTANT: pandas 2.3 retains the input resolution (e.g. datetime64[ms, UTC]).
        # Force ns resolution before comparing to NYSE's int64 nanosecond timestamps.
        nano=ts.dt.as_unit('ns').astype('int64').to_numpy(dtype=np.int64)
        total+=len(nano)
        a=int(nano.min()); b=int(nano.max())
        min_time=a if min_time is None else min(min_time,a)
        max_time=b if max_time is None else max(max_time,b)
        # Quotes are UTC; compare only the actual time instants during XNYS RTH.
        valid=nano[np.isin(nano,grid)]
        if valid.size: chunks.append(valid)
    if total==0 or min_time is None: raise ValueError(f'No valid quote timestamps: {path}')
    first=pd.Timestamp(min_time,unit='ns',tz='UTC')
    last=pd.Timestamp(max_time,unit='ns',tz='UTC')
    if not (pd.Timestamp('2006-01-01',tz='UTC')<first<pd.Timestamp('2027-01-01',tz='UTC')):
        raise ValueError(f'Quote time outside research era: {first} in {path}. Check numeric unit.')
    values=np.unique(np.concatenate(chunks)) if chunks else np.array([],dtype=np.int64)
    if len(values)==0:
        raise RuntimeError(f'ZERO RTH quote timestamps despite valid input! {path}: time range {first} .. {last}. Aborting.')
    info={'source':str(path),'all_rows_valid':total,'invalid_times':bad,'first_timestamp_utc':str(first),
          'last_timestamp_utc':str(last),'rth_unique_labels':int(len(values))}
    print(f'  {path.name}: {total:,} total; {len(values):,} NYSE RTH labels; {first} to {last}',flush=True)
    return values,info


def spy_ts(path, grid, zipmember=None, source_tag=None):
    import zipfile
    print('Reading SPY timestamps:',path,flush=True)
    if zipmember:
        with zipfile.ZipFile(path) as z:
            with z.open(zipmember) as f:
                return _spy_read(f,grid,source_tag)
    with path.open('rb') as f:
        return _spy_read(f,grid,source_tag)


def _spy_read(file, grid, source_tag):
    header=pd.read_csv(file,nrows=0)
    columns=['datetime','source'] if source_tag else ['datetime']
    if any(c not in header.columns for c in columns): raise ValueError('SPY schema changed')
    file.seek(0)
    parts=[]
    for frame in pd.read_csv(file,usecols=columns,chunksize=CHUNK):
        if source_tag: frame=frame.loc[frame.source.astype('string').str.lower().eq(source_tag)]
        if frame.empty:continue
        native=pd.to_datetime(frame.datetime,errors='coerce')
        if native.isna().any(): raise ValueError('SPY has invalid date labels')
        # Same explicit New York CLOCK assumption as original Section 3.2 report.
        utc=native.dt.tz_localize('America/New_York',ambiguous='NaT',nonexistent='NaT').dt.tz_convert('UTC')
        if utc.isna().any(): raise ValueError('Ambiguous SPY local clock timestamps')
        stamps=utc.astype('int64').to_numpy(dtype=np.int64)
        parts.append(stamps[np.isin(stamps,grid)])
    return np.unique(np.concatenate(parts)) if parts else np.array([],dtype=np.int64)


def main():
    assert_timestamp_conversion()
    prev_path=OUT/'summary.json'
    if not prev_path.is_file():raise FileNotFoundError(f'Original Section 3.2 summary missing: {prev_path}')
    prior=json.loads(prev_path.read_text(encoding='utf-8'))
    if prior.get('load_errors'):raise RuntimeError('Earlier audit had source load errors; review before continuing')
    grid=build_grid()
    arrays={}; infos={}
    for key,path in QUOTES.items():
        print('Reading',key,'...',flush=True)
        arrays[key],infos[key]=quote_ts(path,grid)
    both={}
    for asset in ('GOLD','DOLLAR'):
        a,b=arrays[f'{asset}_BID'],arrays[f'{asset}_ASK']
        paired=np.intersect1d(a,b,assume_unique=True)
        assert paired.size>100_000, f'{asset} unexpectedly few aligned quote labels: {len(paired)}'
        both[asset]=paired
        infos[asset+'_PAIR']={'bid_rth':len(a),'ask_rth':len(b),'paired_rth':len(paired),
          'bid_only_rth':int(len(np.setdiff1d(a,b,assume_unique=True))),
          'ask_only_rth':int(len(np.setdiff1d(b,a,assume_unique=True))),
          'pct_of_whole_exchange_grid_NOT_COVERAGE':round(100*len(paired)/len(grid),4),
          'paired_first_utc':str(pd.Timestamp(paired[0],unit='ns',tz='UTC')),
          'paired_last_utc':str(pd.Timestamp(paired[-1],unit='ns',tz='UTC'))}
        print(f'{asset}: {len(paired):,} matching bid/ask XNYS labels',flush=True)

    spy_legacy=spy_ts(RAW/'SPY_clean_1min.csv',grid,source_tag='pitrading')
    spy_raw=spy_ts(DL/'hfdatalibrary_raw_1min_1tickers_2026-10-13.zip',grid,zipmember='SPY_raw_1min.csv')
    spy_overlap={}
    for name,spy in [('SPY_LEGACY',spy_legacy),('SPY_RAW',spy_raw)]:
        for symbol,paired in both.items():
            spy_overlap[f'{name}--{symbol}_PAIRED']={
                'same_label_minutes':int(len(np.intersect1d(spy,paired,assume_unique=True))),
                'warning':'Label overlap does not demonstrate quote freshness or certify historical label boundaries'}

    dst_path=OUT/'dst_examples.csv'
    dst=pd.read_csv(dst_path,dtype={'utc_label':'string'}) if dst_path.is_file() else None
    if dst is not None:
        sample=pd.to_datetime(dst['utc_label'],utc=True).astype('int64').to_numpy(dtype=np.int64)
        for name,paired in both.items():
            dst[name+'_PAIRED']=np.isin(sample,paired).astype(int)
        dst.to_csv(OUT/'dst_examples_CORRECTED.csv',index=False)

    fixed=json.loads(json.dumps(prior))
    fixed['correction_note']='Prior zero quote overlap was an implementation bug: millisecond timestamps were compared to nanosecond exchange-grid values. All new quote timestamps normalized to UTC nanoseconds.'
    fixed['dukascopy_checks']={key:{'bid_rth_labels':int(infos[key+'_PAIR']['bid_rth']),
       'ask_rth_labels':int(infos[key+'_PAIR']['ask_rth']),
       'paired_rth_labels':int(infos[key+'_PAIR']['paired_rth']),
       'bid_only_rth':int(infos[key+'_PAIR']['bid_only_rth']),
       'ask_only_rth':int(infos[key+'_PAIR']['ask_only_rth']),
       'paired_date_span':[infos[key+'_PAIR']['paired_first_utc'],infos[key+'_PAIR']['paired_last_utc']],
       'time_convention':'UTC minute start (documented), actual quote freshness unverified'} for key in both}
    fixed['paired_label_counts'].update(spy_overlap)
    for key in QUOTES:
        fixed['files'][key]['unique_loaded']=infos[key]['rth_unique_labels']
        fixed['files'][key]['note']='UTC timestamp normalized to nanoseconds, then matched to scheduled NYSE minute starts'
    fixed['quote_alignment_correction_details']=infos
    (OUT/'summary_CORRECTED.json').write_text(json.dumps(fixed,indent=2),encoding='utf-8')
    report=[
        '# Section 3.2 — Corrected timestamp/quote alignment report','',
        '**This supplements REPORT.md. The original results are preserved as an audit trail.**','',
        '## Confirmed implementation error','',
        'The previous script converted Unix milliseconds to a pandas datetime64[ms] array but compared its underlying integers to a nanosecond-resolution NYSE calendar. The resulting zero quote overlaps were false.','',
        '## Corrected quote pairing within scheduled NYSE sessions','',
        '| Instrument | Bid labels | Ask labels | Paired labels | Bid-only | Ask-only |',
        '|---|---:|---:|---:|---:|---:|'
    ]
    for key in both:
        item=infos[key+'_PAIR']
        report.append(f'| {key} | {item["bid_rth"]:,} | {item["ask_rth"]:,} | {item["paired_rth"]:,} | {item["bid_only_rth"]:,} | {item["ask_only_rth"]:,} |')
    report += ['','## SPY-versus-quote simultaneous start labels','',
              '| Pair | Matching RTH labels |','|---|---:|']
    for key,obj in spy_overlap.items():
        report.append(f'| {key} | {obj["same_label_minutes"]:,} |')
    report += ['','## Time semantics','',
        '- Modern HF/IEX: New York clock; 09:30 label is the 09:30–09:31 interval based on provider documentation.',
        '- Legacy PiTrading: New York clock is strongly supported by exchange-calendar fit, but start/end labeling remains an assumption.',
        '- Dukascopy: UTC epoch milliseconds; minute-start labels based on original command and exporter evidence.',
        '- Complete 09:30–09:31 minute OHLC is available no earlier than 09:31.',
        '- Same labels are NOT evidence of real-time quote freshness or causality.',
        '- Input files were opened read-only. No cleaning or model evaluation was done.',
        '','## Provenance','',
        '- ETF timing metrics are reused from the previous summary; ETF coverage audits were not rerun.',
        '- Quote-file timestamps and SPY timestamp columns alone were read for this correction.',
        '- `summary_CORRECTED.json` is the authoritative corrected output for Section 3.2.',
    ]
    (OUT/'REPORT_CORRECTED.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print('\nSUCCESS. Outputs:')
    print(OUT/'REPORT_CORRECTED.md')
    print(OUT/'summary_CORRECTED.json')
    if dst is not None:print(OUT/'dst_examples_CORRECTED.csv')
    print('No source files modified. Original report/summary remain unchanged.')

if __name__=='__main__':main()
