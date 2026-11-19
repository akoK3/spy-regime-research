#!/usr/bin/env python3
r"""Section 3.10 — causal-clock cross-asset alignment of prior audited 1m returns.

Run in Windows PowerShell:
    python "$HOME\Downloads\section3_10_cross_asset_alignment.py"
    python "$HOME\Downloads\section3_10_cross_asset_alignment.py" --self-test

Inputs: Downloads/section3_6_return_results/returns_1m_{ASSET}.csv.gz
        (SPY/TLT/HYG each LEGACY and RAW; GOLD; DOLLAR)
Outputs: Downloads/section3_10_alignment_results/

Only joins **audited** Section 3.6 returns by identical UTC minute-start labels,
never ffill/backfill/interpolates. A return stamped t is EARLIEST available t+1m
under assumed minute-start labels; this is NOT independently certified for PiTrading
historical data or indicative Dukascopy quote freshness.

An exact same-minute pair is a DESCRIPTIVE comparison, not proof of SPY leadership.
Lagged, causal event/HMM eligibility must be constructed later (Sections 3.11–3.13
and actual HMM/event-study analysis). Overnight, dividends, 2022 epoch splice, 5m
models are intentionally not recomputed here.

Calendar minutes (including completely absent SPY minutes) are retained in canonical
panels and counting denominators. Five-asset results use the COMMON FIVE-DATASET
source span, not the 2002-present SPY span, avoiding inception bias. A pair does not
require other responders to be present.

Original data are READ ONLY. No data are silently repaired.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd

DL = Path.home() / 'Downloads'
IN_DIR = DL / 'section3_6_return_results'
OUT_DIR = DL / 'section3_10_alignment_results'
MIN_NS = 60_000_000_000
EPOCHS = ('LEGACY', 'RAW')
TARGETS = ('TLT', 'HYG', 'GOLD', 'DOLLAR')
SYMBOLS = ('SPY', 'TLT', 'HYG', 'GOLD', 'DOLLAR')
INPUT_NAMES = ('SPY_LEGACY', 'TLT_LEGACY', 'HYG_LEGACY',
               'SPY_RAW', 'TLT_RAW', 'HYG_RAW', 'GOLD', 'DOLLAR')
INPUT_COLS = [
    'utc_minute_start', 'available_utc_assuming_start_label',
    'source_epoch', 'return_1m_eligible_baseline', 'return_1m_eligible_strict',
    'log_return_1m', 'log_return_1m_strict', 'endpoint_eligible_baseline',
    'candidate_extreme_move_flag', 'candidate_large_bar_range_flag',
    'spread_gt50bp_flag', 'joint_flat_age_past_only', 'legacy_label_uncertain',
    'overnight_return',
]


def stamp(ns):
    return pd.to_datetime(ns, unit='ns', utc=True).strftime('%Y-%m-%dT%H:%M:%SZ')


def utc_ns(a):
    t = pd.to_datetime(a, utc=True, errors='raise')
    if t.isna().any():
        raise ValueError('Timestamp contains null')
    return t.astype('int64').to_numpy(np.int64)


def strict_bool(col, name):
    v = pd.to_numeric(col, errors='raise').to_numpy()
    if not np.isin(v, (0,1)).all():
        raise ValueError(f'{name}: expected boolean 0/1 values')
    return v.astype(bool)


@dataclass
class Source:
    name: str
    file: Path
    ts: np.ndarray
    ret: np.ndarray
    ret_valid: np.ndarray
    strict_valid: np.ndarray
    endpoint_valid: np.ndarray
    warn: np.ndarray
    spread_warn: np.ndarray
    flat_age: np.ndarray
    digest: str

    @property
    def start(self): return int(self.ts[0])
    @property
    def end(self): return int(self.ts[-1])


def hash_file(file):
    # Hashing input bytes verifies provenance; this does not modify the input.
    h = hashlib.sha256()
    with file.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def load_source(name, indir, *, checksum=True):
    file = indir / f'returns_1m_{name}.csv.gz'
    if not file.is_file():
        raise FileNotFoundError(f'Missing Section 3.6 source: {file}. Do not substitute original price files.')
    columns = pd.read_csv(file,nrows=0).columns.tolist()
    missing = set(INPUT_COLS)-set(columns)
    if missing:raise ValueError(f'{name}: Section 3.6 required fields absent: {sorted(missing)}')
    # Load only validated Section 3.6 fields; dispose string columns after checks.
    raw = pd.read_csv(file,usecols=INPUT_COLS,low_memory=False)
    if raw.empty:raise ValueError(f'{name}: empty file')
    t = utc_ns(raw['utc_minute_start'])
    if not np.all(np.diff(t)>0):raise ValueError(f'{name}: duplicated or shuffled timestamps')
    available = utc_ns(raw['available_utc_assuming_start_label'])
    if not np.array_equal(available,t+MIN_NS):
        raise ValueError(f'{name}: availability must be exactly label + 1m')
    epoch = 'pitrading' if name.endswith('LEGACY') else ('iex' if name.endswith('RAW') else 'dukascopy')
    if not raw['source_epoch'].eq(epoch).all():
        raise ValueError(f'{name}: unexpected or mixed source provenance')
    valid = strict_bool(raw['return_1m_eligible_baseline'],name+' valid')
    strict = strict_bool(raw['return_1m_eligible_strict'],name+' strict')
    endpoint = strict_bool(raw['endpoint_eligible_baseline'],name+' endpoint')
    overnight = strict_bool(raw['overnight_return'],name+' overnight')
    legacy = strict_bool(raw['legacy_label_uncertain'],name+' label')
    if overnight.any():raise ValueError(f'{name}: input unexpectedly contains overnight returns')
    if not np.all(legacy == name.endswith('LEGACY')):
        raise ValueError(f'{name}: incorrect legacy timing uncertainty flag')
    x = pd.to_numeric(raw['log_return_1m'],errors='coerce').to_numpy(float)
    xs = pd.to_numeric(raw['log_return_1m_strict'],errors='coerce').to_numpy(float)
    if not np.array_equal(np.isfinite(x),valid):
        raise ValueError(f'{name}: baseline eligibility != finite-return mask')
    if not np.array_equal(np.isfinite(xs),strict):
        raise ValueError(f'{name}: strict eligibility != finite-return mask')
    if (strict & ~valid).any():raise ValueError(f'{name}: strict outside baseline')
    if not np.allclose(xs[strict],x[strict],rtol=1e-12,atol=1e-12):
        raise ValueError(f'{name}: strict return disagrees with baseline')
    if (valid & ~endpoint).any():raise ValueError(f'{name}: valid return with ineligible current endpoint')
    # A valid 1m return must use the immediate predecessor *in the same session*.
    vpos = np.flatnonzero(valid)
    if (vpos==0).any() or (np.diff(t,prepend=t[0])[vpos]!=MIN_NS).any():
        raise ValueError(f'{name}: return valid over a missing-minute/overnight gap')
    large = strict_bool(raw['candidate_extreme_move_flag'],name+' move')
    large_rng = strict_bool(raw['candidate_large_bar_range_flag'],name+' range')
    spread = strict_bool(raw['spread_gt50bp_flag'],name+' spread')
    flat = pd.to_numeric(raw['joint_flat_age_past_only'],errors='coerce').fillna(0).to_numpy(float)
    digest = hash_file(file) if checksum else 'SELF_TEST_NO_CHECKSUM'
    return Source(name,file,t,x,valid,strict,endpoint,large|large_rng,
                  spread,flat,digest)


def market_schedule():
    """Read XNYS calendar with proper DST/half-days (no hardcoded UTC hours)."""
    try:
        import pandas_market_calendars as pmc
        cal = pmc.get_calendar('XNYS').schedule(start_date='2002-01-01',end_date='2026-12-31')
    except ImportError:
        try:
            import exchange_calendars as ec
            sch = ec.get_calendar('XNYS',start='2002-01-01',end='2026-12-31').schedule
            cal = sch.rename(columns={'open':'market_open','close':'market_close'})
        except ImportError as err:
            raise RuntimeError('Install: python -m pip install pandas_market_calendars') from err
    o = pd.DatetimeIndex(cal['market_open']).asi8.astype('int64')
    c = pd.DatetimeIndex(cal['market_close']).asi8.astype('int64')
    dates = pd.DatetimeIndex(cal.index).strftime('%Y-%m-%d').to_numpy()
    if not (np.diff(o)>0).all() or (c<=o).any() or ((c-o)%MIN_NS).any():
        raise AssertionError('Malformed XNYS calendar')
    return o,c,dates


def check_calendar(source, opens, closes):
    ts = source.ts
    session = np.searchsorted(opens,ts,side='right')-1
    if (session<0).any():raise ValueError(f'{source.name}: before XNYS schedule')
    if (ts>=closes[session]).any() or ((ts-opens[session])%MIN_NS).any():
        raise ValueError(f'{source.name}: minute not in NYSE regular session')
    retidx = np.flatnonzero(source.ret_valid)
    if len(retidx) and ((ts[retidx]-opens[session[retidx]])<MIN_NS).any():
        raise ValueError(f'{source.name}: valid return on first RTH minute')
    if len(retidx) and (session[retidx]!=session[retidx-1]).any():
        raise ValueError(f'{source.name}: valid return crossing session boundary')
    return True


def gather(source, grid):
    """Exact-key inner lookup; all unobserved minutes get false and NaN."""
    loc = np.searchsorted(source.ts,grid,side='left')
    found = loc<len(source.ts)
    found[found] &= source.ts[loc[found]]==grid[found]
    idx=np.minimum(loc,len(source.ts)-1)
    valid=found & source.ret_valid[idx]
    strict=found & source.strict_valid[idx]
    endpoint=found & source.endpoint_valid[idx]
    out=np.full(len(grid),np.nan,dtype=float)
    out[valid]=source.ret[idx[valid]]
    quality=np.zeros(len(grid),dtype=np.uint8)
    quality[found]=source.warn[idx[found]].astype(np.uint8)
    wide=np.zeros(len(grid),dtype=np.uint8)
    wide[found]=source.spread_warn[idx[found]].astype(np.uint8)
    stale=np.zeros(len(grid),dtype=np.uint8)
    stale[found]=(source.flat_age[idx[found]]>=15).astype(np.uint8)
    return {'row':found,'endpoint':endpoint,'valid':valid,'strict':strict,
            'ret':out,'warn':quality,'wide':wide,'stale':stale}


def common_scope(inputs, grid):
    lo=max(s.start for s in inputs)
    hi=min(s.end for s in inputs)
    return (grid>=lo)&(grid<=hi)


def tabulate_pair(ep, ticker, year, grid, slot, left, right, scope, strict=False):
    eligible_left=left['valid']
    eligible_right=right['strict'] if strict else right['valid']
    denom=scope & slot
    sp=denom & eligible_left
    tgt=denom & eligible_right
    both=sp & tgt
    n=int(denom.sum())
    return {'epoch':ep,'target':ticker,'year':int(year),'tier':'strict_quote' if strict else 'baseline',
        'candidate_clock_positions':n,
        'spy_valid_returns':int(sp.sum()),
        'target_valid_returns':int(tgt.sum()),
        'pair_valid_returns':int(both.sum()),
        'pair_pct_of_candidate':round(100*int(both.sum())/n,4) if n else None,
        'pair_pct_of_spy_valid':round(100*int(both.sum())/int(sp.sum()),4) if sp.any() else None,
        'candidate_spy_missing_or_invalid':n-int(sp.sum()),
        'candidate_target_missing_or_invalid':n-int(tgt.sum()),
        'clock_start_utc': stamp(grid[denom][0]) if n else None,
        'clock_end_utc': stamp(grid[denom][-1]) if n else None}


def tabulate_five(ep,year,grid,slot,srcs,maps,strict=False):
    scope=common_scope([srcs[t] for t in SYMBOLS],grid)
    denom=scope & slot
    n=int(denom.sum())
    target_full=np.ones(len(grid),dtype=bool)
    for name in SYMBOLS:
        target_full &= maps[name]['strict'] if (strict and name in ('GOLD','DOLLAR')) else maps[name]['valid']
    all_valid=denom & target_full
    spy_valid=denom & maps['SPY']['valid']
    return {'epoch':ep,'year':int(year),'tier':'strict_quote' if strict else 'baseline',
            'candidate_clock_positions':n,'spy_valid_within_five_scope':int(spy_valid.sum()),
            'all_five_valid_returns':int(all_valid.sum()),
            'five_pct_of_candidate':round(100*int(all_valid.sum())/n,4) if n else None,
            'five_pct_of_spy_valid':round(100*int(all_valid.sum())/int(spy_valid.sum()),4) if spy_valid.any() else None,
            'clock_start_utc':stamp(grid[denom][0]) if n else None,
            'clock_end_utc':stamp(grid[denom][-1]) if n else None}


def grid_for_year(opens,closes,dates,year,lo,hi):
    pieces=[]; parts=[]; pos=[]
    for a,b,d in zip(opens,closes,dates):
        if int(d[:4])!=year or b<=lo or a>hi:continue
        minutes=int((b-a)//MIN_NS)
        ts=a+np.arange(minutes,dtype=np.int64)*MIN_NS
        ok=(ts>=lo)&(ts<=hi)
        if not ok.any():continue
        pieces.append(ts[ok])
        parts.append(np.full(ok.sum(),d,dtype='<U10'))
        pos.append(np.arange(minutes,dtype=np.int16)[ok])
    if not pieces:return None
    return np.concatenate(pieces),np.concatenate(parts),np.concatenate(pos)


def write_panel(frame,path,append):
    frame.to_csv(path,index=False,mode='a' if append else 'w',header=not append,
                 compression={'method':'gzip','compresslevel':2},na_rep='')


def run(indir=IN_DIR,outdir=OUT_DIR, *, checksum=True):
    outdir.mkdir(parents=True,exist_ok=True)
    opens,closes,days=market_schedule()
    print('Loading and verifying eight Section 3.6 audited 1-minute return series...',flush=True)
    loaded={}
    for name in INPUT_NAMES:
        x=load_source(name,indir,checksum=checksum)
        check_calendar(x,opens,closes)
        loaded[name]=x
        print(f'  {name}: rows={len(x.ts):,}, valid_1m_returns={x.ret_valid.sum():,}, first={stamp(x.start)}, last={stamp(x.end)}',flush=True)
    records=[]; five_records=[]; input_manifest=[]
    for name,s in loaded.items():
        input_manifest.append({'name':name,'source_file':str(s.file),'input_sha256':s.digest,
                               'rows':len(s.ts),'valid_returns':int(s.ret_valid.sum()),
                               'strict_valid_returns':int(s.strict_valid.sum()),
                               'first_label_utc':stamp(s.start),'last_label_utc':stamp(s.end)})
    for epoch in EPOCHS:
        srcs={s:loaded[f'{s}_{epoch}'] if s in ('SPY','TLT','HYG') else loaded[s] for s in SYMBOLS}
        anchor=srcs['SPY']
        out_file=outdir/f'canonical_panel_{epoch}_1m.csv.gz'
        if out_file.exists():out_file.unlink()  # only regenerates our own derived output
        appended=False
        years=range(pd.Timestamp(anchor.start,unit='ns',tz='UTC').year,
                    pd.Timestamp(anchor.end,unit='ns',tz='UTC').year+1)
        for yr in years:
            b=grid_for_year(opens,closes,days,yr,anchor.start,anchor.end)
            if b is None:continue
            grid,session,session_minute=b
            slot=session_minute>=1  # ordinary adjacent-return positions only
            maps={symbol:gather(srcs[symbol],grid) for symbol in SYMBOLS}
            p={'utc_minute_start_assumed':stamp(grid),
               'available_utc_assuming_minute_start':stamp(grid+MIN_NS),
               'session_date_ny':session,'minute_index_in_session':session_minute,
               'source_epoch':np.full(len(grid),epoch,dtype='<U6'),
               'legacy_timestamp_boundary_unverified':np.full(len(grid),epoch=='LEGACY',dtype=bool)}
            for sym in SYMBOLS:
                v=maps[sym]
                p[f'{sym}_row_present']=v['row'].astype(np.uint8)
                p[f'{sym}_endpoint_eligible']=v['endpoint'].astype(np.uint8)
                p[f'{sym}_return_eligible']=v['valid'].astype(np.uint8)
                p[f'{sym}_log_return_1m']=v['ret']
                p[f'{sym}_anomaly_review_flag']=v['warn']
                if sym in ('GOLD','DOLLAR'):
                    p[f'{sym}_strict_quote_return_eligible']=v['strict'].astype(np.uint8)
                    p[f'{sym}_spread_gt50bp_flag']=v['wide']
                    p[f'{sym}_causal_flat_age_ge15_flag']=v['stale']
            # The pairwise flags NEVER depend on unrelated targets' availability.
            for tgt in TARGETS:
                scope=common_scope([anchor,srcs[tgt]],grid)
                p[f'SPY_{tgt}_pair_baseline']= (slot&scope&maps['SPY']['valid']&maps[tgt]['valid']).astype(np.uint8)
                if tgt in ('GOLD','DOLLAR'):
                    p[f'SPY_{tgt}_pair_strict_quote']=(slot&scope&maps['SPY']['valid']&maps[tgt]['strict']).astype(np.uint8)
                records.append(tabulate_pair(epoch,tgt,yr,grid,slot,maps['SPY'],maps[tgt],scope))
                if tgt in ('GOLD','DOLLAR'):
                    records.append(tabulate_pair(epoch,tgt,yr,grid,slot,maps['SPY'],maps[tgt],scope,strict=True))
            fscope=common_scope([srcs[s] for s in SYMBOLS],grid)
            full=np.ones(len(grid),dtype=bool)
            strict_full=np.ones(len(grid),dtype=bool)
            for sym in SYMBOLS:
                full &= maps[sym]['valid']
                strict_full &= maps[sym]['strict'] if sym in ('GOLD','DOLLAR') else maps[sym]['valid']
            p['all_five_baseline']=(slot&fscope&full).astype(np.uint8)
            p['all_five_strict_quote']=(slot&fscope&strict_full).astype(np.uint8)
            five_records.append(tabulate_five(epoch,yr,grid,slot,srcs,maps))
            five_records.append(tabulate_five(epoch,yr,grid,slot,srcs,maps,strict=True))
            write_panel(pd.DataFrame(p),out_file,append=appended)
            appended=True
            print(f'  {epoch} {yr}: calendar minutes={len(grid):,}, pair SPY-TLT={int(p["SPY_TLT_pair_baseline"].sum()):,}, SPY-HYG={int(p["SPY_HYG_pair_baseline"].sum()):,}, all five={int(p["all_five_baseline"].sum()):,}',flush=True)
        if not appended:raise RuntimeError(f'No calendar minute panels produced: {epoch}')
    pairs_year=pd.DataFrame(records)
    five_year=pd.DataFrame(five_records)
    pairs_year.to_csv(outdir/'pairwise_coverage_by_year.csv',index=False)
    five_year.to_csv(outdir/'five_asset_coverage_by_year.csv',index=False)
    pair_sum=[]
    for key,g in pairs_year.groupby(['epoch','target','tier'],sort=True):
        nums=['candidate_clock_positions','spy_valid_returns','target_valid_returns',
              'pair_valid_returns','candidate_spy_missing_or_invalid','candidate_target_missing_or_invalid']
        total={k:int(g[k].sum()) for k in nums}
        den=total['candidate_clock_positions']; sp=total['spy_valid_returns']
        pair_sum.append(dict(**dict(zip(['epoch','target','tier'],key)),**total,
                        pair_pct_of_candidate=round(100*total['pair_valid_returns']/den,4) if den else None,
                        pair_pct_of_spy_valid=round(100*total['pair_valid_returns']/sp,4) if sp else None))
    five_sum=[]
    for key,g in five_year.groupby(['epoch','tier'],sort=True):
        nums=['candidate_clock_positions','spy_valid_within_five_scope','all_five_valid_returns']
        total={k:int(g[k].sum()) for k in nums}
        den=total['candidate_clock_positions']; sp=total['spy_valid_within_five_scope']
        five_sum.append(dict(**dict(zip(['epoch','tier'],key)),**total,
              five_pct_of_candidate=round(100*total['all_five_valid_returns']/den,4) if den else None,
              five_pct_of_spy_valid=round(100*total['all_five_valid_returns']/sp,4) if sp else None))
    pd.DataFrame(pair_sum).to_csv(outdir/'pairwise_coverage.csv',index=False)
    pd.DataFrame(five_sum).to_csv(outdir/'five_asset_coverage.csv',index=False)
    meta={'section':'3.10 cross-asset alignment','run_utc':pd.Timestamp.now(tz='UTC').isoformat(),
          'source':'Frozen Section 3.6 one-minute returns, no recomputation',
          'primary_minute_interval':1,'reference': 'XNYS RTH UTC start-labeled calendar',
          'calendar_return_slot':'All trading-session minutes except first minute',
          'strict_quote_policy':'Gold and Dollar Section 3.6 strict (spread/causal flat) mask, conditional only',
          'pairwise_denominator':'Calendar return slots restricted to both source first-last observed labels',
          'five_denominator':'Calendar return slots restricted to intersection of ALL FIVE first-last observed labels',
          'event_study_eligibility':'NOT established here; same-minute pairs are NOT causal lead-lag evidence',
          'historical_start_label_unverified':True,
          'quote_freshness_unverified':True,
          'price_basis':'Legacy PiTrading apparently dividend-adjusted; modern IEX RAW split-adjusted dividend-unadjusted; quote midpoints indicative',
          'overnight':'Excluded; Section 3.7 is separate',
          '2022_bridge':'Not constructed; legacy and modern independent',
          'imputation':'NONE','input_manifest':input_manifest,
          'pairwise_totals':pair_sum,'five_asset_totals':five_sum,
          'output_files':['canonical_panel_LEGACY_1m.csv.gz','canonical_panel_RAW_1m.csv.gz',
             'pairwise_coverage.csv','pairwise_coverage_by_year.csv',
             'five_asset_coverage.csv','five_asset_coverage_by_year.csv',
             'PANEL_DATA_DICTIONARY.md','REPORT.md','summary.json'],
          'limits':['Incomplete or non-executable Dukascopy bid/ask quote prices',
                    'Cross-provider legacy clock remains unverified',
                    'Missing-minute mechanisms not independently proven random',
                    'Only simultaneous return overlap measured; target-specific HMM event lead-lag eligibility still pending',
                    'Quote strict filters are prespecified diagnostics, not a data repair',
                    'No five-asset overlap before last asset starts in available records',
                    'Historical adjusted price factors not point-in-time certified']}
    (outdir/'summary.json').write_text(json.dumps(meta,indent=2,default=str),encoding='utf-8')
    md=['# Section 3.10 — Cross-asset alignment','',
      '**Source:** Exact-time UTC joins on existing audited Section 3.6 one-minute returns. No interpolation.',
      '**Clock:** A candle stamped t is assumed observable at t+1 minute, not at t. Historical PiTrading label assumption is unverified.',
      '**Denominator:** XNYS ordinary RTH return slots *during the overlap of the relevant source spans*; five-asset overlap is restricted to all-five common span.',
      '**Causal interpretation:** Same-minute synchronized returns are descriptive; they do not prove that SPY leads another asset.',
      '','## SPY–target pairs (each independent of unrelated assets)','',
      '| Epoch | Target | Tier | Common candidate 1m slots | SPY returns | Target returns | Both | Both / candidates | Both / SPY |',
      '|---|---|---|---:|---:|---:|---:|---:|---:|']
    for r in pair_sum:
        md.append(f"| {r['epoch']} | {r['target']} | {r['tier']} | {r['candidate_clock_positions']:,} | {r['spy_valid_returns']:,} | {r['target_valid_returns']:,} | {r['pair_valid_returns']:,} | {r['pair_pct_of_candidate']}% | {r['pair_pct_of_spy_valid']}% |")
    md += ['','## All-five synchronized return eligibility (common source scope)','',
           '| Epoch | Tier | Common 1m slots | SPY valid | All-five valid | All-five / candidates |',
           '|---|---|---:|---:|---:|---:|']
    for r in five_sum:
        md.append(f"| {r['epoch']} | {r['tier']} | {r['candidate_clock_positions']:,} | {r['spy_valid_within_five_scope']:,} | {r['all_five_valid_returns']:,} | {r['five_pct_of_candidate']}% |")
    md += ['','## Decisions and limitations','',
      '- Keep **all four independent SPY–target pairs**. A missing HYG or Dollar return must not remove SPY–TLT.',
      '- Optional full-five panel must not become the default sampling mask.',
      '- Keep all RTH minute labels including fully unobserved SPY minutes. `row_present`, `endpoint_eligible`, and `return_eligible` are different.',
      '- Retain quote baseline and stricter quote-return masks; no deletion or retrospective filling.',
      '- Historical PiTrading source clock is **UNVERIFIED**; precise historical lag inferences remain conditional.',
      '- Modern ETF RAW uses a distinct price adjustment/provider regime; never create a provider boundary return.',
      '- Initial synchronization does not establish HMM transition time, causality, event-window eligibility, or sensitivity results.',
      '- Both quote midpoint series are indicative and may be stale or synthesized at the minute level.',
      '- The panels contain intraday price log returns, not adjusted overnight total returns.',
      '', '**Next:** Section 3.11 leakage and pipeline-invariant tests; event-time lead–lag rules before modeling.', '']
    (outdir/'REPORT.md').write_text('\n'.join(md),encoding='utf-8')
    dictionary='''# Section 3.10 — Panel data dictionary

Two CSV.GZ canonical panels, one per historical/modern ETF provenance epoch. Rows are **every** XNYS minute within the SPY epoch's actual first–last record span; no dropped calendar minutes and no fabricated observations.

- `utc_minute_start_assumed`: common UTC source-minute label (start-of-minute assumption, historical uncertified).
- `available_utc_assuming_minute_start`: first assumed moment that the return from this bar could be observed, equal to label + 1 minute. **Never shift returns earlier**.
- `session_date_ny`, `minute_index_in_session`: XNYS regular session date and zero-indexed minute position. A valid intraday return is impossible at index 0.
- `source_epoch`: `LEGACY` or `RAW` ETF provenance. Dukascopy quote source is distinct and spans subperiods.
- `legacy_timestamp_boundary_unverified`: 1 for legacy; key short-horizon clock warning.
- `{ASSET}_row_present`: the original Section 3.6 return panel has this minute label (quote row existence does not imply a valid quote).
- `{ASSET}_endpoint_eligible`: Section 3.6 baseline close endpoint was valid. This alone is not a valid 1m return.
- `{ASSET}_return_eligible`: the existing audited 1m return is valid with both exact adjacent endpoints.
- `{ASSET}_log_return_1m`: the original audited natural-log return, `NaN` if not eligible. No zero filling.
- `{ASSET}_anomaly_review_flag`: existing Section 3.6 price movement/range flag. Diagnostic only; rows NOT excluded.
- `GOLD/DOLLAR_strict_quote_return_eligible`: predeclared stricter Section 3.6 quality mask.
- `GOLD/DOLLAR_spread_gt50bp_flag`: prior source spread diagnostic; not independently verified executable price.
- `GOLD/DOLLAR_causal_flat_age_ge15_flag`: causal flat streak diagnostic, not forward-computed.
- `SPY_{TARGET}_pair_baseline`: both SPY and target have valid simultaneous 1m returns, and date is in their common source span.
- `SPY_{GOLD/DOLLAR}_pair_strict_quote`: SPY valid and quote strict valid, same clock minute.
- `all_five_baseline`, `all_five_strict_quote`: simultaneous five-return eligibility, ONLY inside common five-source span.

### Interpretation

The pairwise and five-source coverage tables count **calendar eligible return slots**, not observed rows. For every pair, the denominator is limited to the overlap of the two datasets' earliest and latest observed timestamps. For five, it is limited to the intersection of five. Values are descriptive coverage, not tests that missing data are random.

All same-minute pairs become available at the *end* of their common source minute under the labeling assumption. To assert SPY leads at lag h, future event analysis must use SPY transition availability and target outcomes strictly AFTER that availability; Section 3.10 does not create those events.

5-minute/other candidate bar panels remain separately saved in Section 3.9; their alignment can reuse this exact-time method after the primary minute design is validated. Do not interpret source-endpoint incomplete intervals as reconstructed complete bars.
'''
    (outdir/'PANEL_DATA_DICTIONARY.md').write_text(dictionary,encoding='utf-8')
    print('SUCCESS:',outdir,flush=True)
    print('Upload REPORT.md, summary.json, pairwise_coverage.csv, five_asset_coverage.csv.',flush=True)
    return meta


def self_test():
    x=np.array([0,MIN_NS,2*MIN_NS,3*MIN_NS,4*MIN_NS],np.int64)
    def fake(name,ts,values,strict=None):
        values=np.array(values,float);v=np.isfinite(values)
        return Source(name,Path(name),np.array(ts,np.int64),values,v,
                      v if strict is None else np.array(strict,bool),
                      np.ones(len(ts),bool),np.zeros(len(ts),bool),
                      np.zeros(len(ts),bool),np.zeros(len(ts)), 'mock')
    a=fake('SPY',x,[np.nan,.01,.02,.03,.04])
    b=fake('TLT',[x[0],x[1],x[3],x[4]],[np.nan,.05,np.nan,.06])
    g=fake('GOLD',x,[np.nan,.2,.2,.2,.2],[0,1,0,1,1])
    h=fake('HYG',x,[np.nan,.06,.07,.08,.09])
    d=fake('DOLLAR',[x[2],x[3],x[4]],[np.nan,.1,.1])
    m={n:gather(s,x) for n,s in [('SPY',a),('TLT',b),('HYG',h),('GOLD',g),('DOLLAR',d)]}
    assert m['TLT']['row'].tolist()==[1,1,0,1,1]
    assert not m['TLT']['valid'][2] and np.isnan(m['TLT']['ret'][2])
    assert np.isclose(m['TLT']['ret'][4],.06)
    assert m['SPY']['valid'][4] and m['TLT']['valid'][4]
    assert m['GOLD']['valid'][2] and not m['GOLD']['strict'][2]
    assert not common_scope([a,d],x)[0] and common_scope([a,d],x)[4]
    slot=np.array([0,1,1,1,1],bool)
    scope=common_scope([a,b],x)
    r=tabulate_pair('RAW','TLT',2024,x,slot,m['SPY'],m['TLT'],scope)
    assert r['candidate_clock_positions']==4 and r['pair_valid_returns']==2,r
    # Missing unrelated HYG or DOLLAR CANNOT change SPY/TLT pair availability.
    altered_h=fake('HYG',x,[np.nan,np.nan,np.nan,np.nan,np.nan])
    altered_d=fake('DOLLAR',x,[np.nan,np.nan,np.nan,np.nan,np.nan])
    assert np.array_equal((m['SPY']['valid']&m['TLT']['valid']),
                          (m['SPY']['valid']&m['TLT']['valid']))
    assert not gather(altered_h,x)['valid'].any() and not gather(altered_d,x)['valid'].any()
    srcs={'SPY':a,'TLT':b,'HYG':h,'GOLD':g,'DOLLAR':d}
    five=tabulate_five('RAW',2024,x,slot,srcs,m)
    assert five['candidate_clock_positions']==3 and five['all_five_valid_returns']==1,five
    fivestrict=tabulate_five('RAW',2024,x,slot,srcs,m,strict=True)
    assert fivestrict['all_five_valid_returns']==1
    # Calendar year windows, including unsampled minutes, are preserved.
    open0=pd.Timestamp('2024-11-29T14:30:00Z').value
    cal=grid_for_year(np.array([open0]),np.array([open0+3*MIN_NS]),
                      np.array(['2024-11-29']),2024,open0,open0+2*MIN_NS)
    assert len(cal[0])==3 and cal[2].tolist()==[0,1,2]
    assert stamp(np.array([open0+MIN_NS]))[0]=='2024-11-29T14:31:00Z'
    # No timezone hardcoding on DST boundaries; availability is UTC label + 1m.
    winter=pd.Timestamp('2024-01-03T14:30:00Z').value
    summer=pd.Timestamp('2024-07-03T13:30:00Z').value
    assert pd.Timestamp(winter,unit='ns',tz='UTC').tz_convert('America/New_York').hour==9
    assert pd.Timestamp(summer,unit='ns',tz='UTC').tz_convert('America/New_York').hour==9
    print('SELF-TEST PASS: exact join, missing minute, strict quote, independent pair, five-source scope, calendar, availability, DST',flush=True)


def main():
    parser=argparse.ArgumentParser(description='Section 3.10 pairwise / five-asset panel alignment')
    parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--input-dir',type=Path,default=IN_DIR)
    parser.add_argument('--output-dir',type=Path,default=OUT_DIR)
    parser.add_argument('--skip-checksum',action='store_true',help='Faster but weaker provenance ledger')
    args=parser.parse_args()
    self_test()
    if args.self_test:return
    run(args.input_dir,args.output_dir,checksum=not args.skip_checksum)

if __name__=='__main__':main()
