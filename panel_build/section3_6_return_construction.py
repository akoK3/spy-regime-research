#!/usr/bin/env python3
r"""Research Section 3.6 — audited, gap-aware one-minute log returns.

Run on Windows PowerShell:
    python "$HOME\Downloads\section3_6_return_construction.py"
Test without source files:
    python "$HOME\Downloads\section3_6_return_construction.py" --self-test

Dependencies: numpy, pandas. Inputs are existing locally generated *3.4 ETF*
observed-bar panels and *3.5 gold/dollar* quote-quality panels. NO raw market
files are modified. Does not fill missing prices or splice vendor epochs.

Decision boundaries:
- 1m returns only when *both* observed endpoints are one scheduled minute
  apart in the SAME NYSE session.
- Paired quote CLOSE midpoint is indicative and may contain asynchronous quotes;
  it is neither an executable price nor independently time-verified.
- Primary ETF output is *price* log return, NOT total return.
- Legacy minute-start labeling is UNVERIFIED: availability assumes start label.
- No dividends/ex-dates or overnight returns are repaired in this section.
- Strict quote sensitivity is PRE-SPECIFIED and applied to both return endpoints.
- Retrospective gaps are for diagnostics, not model features.
"""
from __future__ import annotations
import argparse
import json
import math
import warnings
from pathlib import Path
import numpy as np
import pandas as pd

MINUTE_NS = 60_000_000_000
SOURCES_ETF = ('SPY_LEGACY', 'TLT_LEGACY', 'HYG_LEGACY', 'SPY_RAW', 'TLT_RAW', 'HYG_RAW')
SOURCES_QUOTE = ('GOLD', 'DOLLAR')
HOME = Path.home()
DL = HOME / 'Downloads'
ETF_DIR = DL / 'section3_4_etf_results'
QUOTE_DIR = DL / 'section3_5_quote_quality_results'
OUT = DL / 'section3_6_return_results'
CHUNK = 250_000


def utc_ns(stamps: pd.Series) -> np.ndarray:
    converted = pd.to_datetime(stamps, utc=True, errors='raise')
    if converted.isna().any():
        raise ValueError('Missing timestamp in input')
    return converted.astype('int64').to_numpy(dtype=np.int64)


def iso(ns: int) -> str:
    return pd.Timestamp(int(ns), unit='ns', tz='UTC').isoformat().replace('+00:00', 'Z')


def valid_num(x: np.ndarray) -> np.ndarray:
    return np.isfinite(x) & (x > 0)


def calculate_step(stamps: np.ndarray, sessions: np.ndarray,
                   prices: np.ndarray, endpoint_base: np.ndarray,
                   endpoint_strict: np.ndarray | None = None) -> dict:
    """Online-safe return eligibility for full observations *or* a chunk with
    prior row prepended. Only current and immediately preceding rows used.
    Session identifier MUST be a normalized, calendar-grounded NYSE date.
    """
    n = len(stamps)
    if endpoint_strict is None:
        endpoint_strict = endpoint_base
    if not (len(sessions)==len(prices)==len(endpoint_base)==len(endpoint_strict)==n):
        raise ValueError('Mismatched data lengths')
    if n > 1 and not (np.diff(stamps) > 0).all():
        raise ValueError('Unsorted or duplicated minute labels')
    endpoint_base = np.asarray(endpoint_base,dtype=bool) & valid_num(prices)
    endpoint_strict = np.asarray(endpoint_strict,dtype=bool) & endpoint_base
    adjacent = np.zeros(n,dtype=bool)
    same_sess = np.zeros(n,dtype=bool)
    elapsed = np.zeros(n,dtype=np.int32)
    elapsed[:] = -1
    if n > 1:
        delta = stamps[1:] - stamps[:-1]
        same_sess[1:] = (sessions[1:]==sessions[:-1])
        adjacent[1:] = (delta==MINUTE_NS)&same_sess[1:]
        same_pos = same_sess[1:] & (delta % MINUTE_NS == 0)
        elapsed[1:][same_pos] = (delta[same_pos]//MINUTE_NS).astype(np.int32)
    baseline = np.zeros(n,dtype=bool)
    strict = np.zeros(n,dtype=bool)
    if n>1:
        baseline[1:] = adjacent[1:] & endpoint_base[1:] & endpoint_base[:-1]
        strict[1:] = adjacent[1:] & endpoint_strict[1:] & endpoint_strict[:-1]
    ret = np.full(n, np.nan,dtype=float)
    ret_strict = np.full(n,np.nan,dtype=float)
    eligible_idx = np.flatnonzero(baseline)
    if len(eligible_idx):
        ret[eligible_idx] = np.log(prices[eligible_idx]/prices[eligible_idx-1])
    eligible_strict_idx = np.flatnonzero(strict)
    if len(eligible_strict_idx):
        ret_strict[eligible_strict_idx] = ret[eligible_strict_idx]
    # All statuses are computable using only history through current minute.
    status = np.full(n, 'PRIOR_BAR_NOT_ADJACENT', dtype='<U34')
    if n:
        status[0] = 'START_OF_INPUT_OR_CHUNK'
    status[~endpoint_base] = 'CURRENT_ENDPOINT_INELIGIBLE'
    if n>1:
        session_change = ~same_sess[1:]
        status[1:][session_change & endpoint_base[1:]] = 'NEW_SESSION_NO_INTRADAY_RETURN'
        same_missing = same_sess[1:] & ~adjacent[1:] & endpoint_base[1:]
        status[1:][same_missing] = 'PRIOR_MINUTE_MISSING'
        prior_bad = adjacent[1:] & (~endpoint_base[:-1]) & endpoint_base[1:]
        status[1:][prior_bad] = 'PRIOR_ENDPOINT_INELIGIBLE'
    status[baseline] = 'VALID_1M_RETURN'
    return dict(adjacent=adjacent, same_session=same_sess, elapsed=elapsed,
                baseline=baseline, strict=strict, ret=ret, ret_strict=ret_strict,
                status=status, endpoint_base=endpoint_base, endpoint_strict=endpoint_strict)


def self_tests() -> None:
    t=np.arange(7,dtype=np.int64)*MINUTE_NS
    ss=np.array(['A','A','A','A','A','B','B'])
    px=np.array([100.,101.,102.,103.,104.,105.,106.])
    # Minute 2 missing; minute 3 cannot be bridged with minute 1.
    choose=np.array([0,1,3,4,5,6])
    z=calculate_step(t[choose],ss[choose],px[choose],np.ones(len(choose),dtype=bool))
    assert z['baseline'].tolist()==[False,True,False,True,False,True],z['status']
    assert np.isnan(z['ret'][2]);assert z['elapsed'][2]==2
    assert z['status'][2]=='PRIOR_MINUTE_MISSING'
    assert z['status'][4]=='NEW_SESSION_NO_INTRADAY_RETURN'
    assert np.isclose(z['ret'][1], math.log(101/100))
    assert z['baseline'][3] and not z['baseline'][4]
    # Strict is two-ended; filtering the earlier endpoint removes current return.
    strict=np.array([1,0,1,1,1,1],dtype=bool)
    a=calculate_step(t[choose],ss[choose],px[choose],np.ones(6,dtype=bool),strict)
    assert not a['strict'][1] and a['strict'][3]
    # Present midpoints with absent prior side must not inherit old quotes.
    base=np.array([True,False,True,True],dtype=bool)
    y=calculate_step(np.arange(4)*MINUTE_NS,np.array(['A']*4),
                     np.array([100.,np.nan,102.,103.]),base)
    assert y['baseline'].tolist()==[False,False,False,True]
    assert np.isnan(y['ret'][2]); assert np.isclose(y['ret'][3],np.log(103/102))
    # A zero RETURN from two genuinely identical adjacent prices is legitimate.
    j=calculate_step(np.array([0,MINUTE_NS]),np.array(['A','A']),np.array([100.,100.]),np.ones(2,bool))
    assert j['ret'][1]==0.0 and j['baseline'][1]
    # Changing FUTURE records cannot alter earlier eligibility or return.
    k=calculate_step(t[choose],ss[choose],np.array([100.,101.,103.,104.,10000.,106.]),np.ones(6,bool))
    assert np.allclose(z['ret'][:4],k['ret'][:4],equal_nan=True)
    # Synthetic source-epoch split never generates a valid return even on adjacent timestamps.
    b=calculate_step(np.array([0,MINUTE_NS]),np.array(['LEGACY','MODERN']),np.array([100.,101.]),np.ones(2,bool))
    assert not b['baseline'][1]
    print('SELF-TEST PASS: gaps, sessions, log returns, zero changes, two-ended strict, causality, epoch boundary',flush=True)


def base_name(kind: str, name: str) -> Path:
    return ETF_DIR / f'etf_observed_{name}.csv.gz' if kind=='ETF' else QUOTE_DIR / f'quote_quality_rth_{name}.csv.gz'


def prepare_batch(kind: str, name: str, chunk: pd.DataFrame) -> pd.DataFrame:
    """Normalize prior outputs; verify dates and source IDs, not original files."""
    if kind=='ETF':
        cols={'utc_minute_start','session_date_ny','Close','review_move_gt_200bp','review_range_gt_200bp',
              'source_epoch','legacy_minute_start_assumed_unverified','causal_prev_minute_log_move_bp'}
        if not cols.issubset(chunk):
            raise ValueError(f'{name}: 3.4 output schema not recognized; missing {cols-set(chunk)}')
        res=pd.DataFrame({'utc_minute_start':chunk['utc_minute_start'],
          'session_date_ny':chunk['session_date_ny'].astype(str),
          'price':pd.to_numeric(chunk['Close'], errors='coerce'),
          'endpoint_base':1,
          'endpoint_strict':1,
          'flag_jump':chunk['review_move_gt_200bp'].astype(np.uint8),
          'flag_range':chunk['review_range_gt_200bp'].astype(np.uint8),
          'spread_gt50':0,'flat_age':0,
          'source_epoch':chunk['source_epoch'].astype(str),
          'legacy_label_uncertain':chunk['legacy_minute_start_assumed_unverified'].astype(np.uint8),
          'source_3_4_return_bp':pd.to_numeric(chunk['causal_prev_minute_log_move_bp'],errors='coerce')})
        expected='pitrading' if name.endswith('LEGACY') else 'iex'
        if (res['source_epoch']!=expected).any():
            raise ValueError(f'{name}: unexpected source label')
        return res
    cols={'utc_minute_start','mid_close','status','baseline_paired_non_crossed',
          'sensitivity_spread50_flat15_eligible','mid_return_1m_bp_only_adjacent_paired',
          'mid_abs_jump_review_flag','spread_gt50bp_flag','joint_flat_age_past_only'}
    if not cols.issubset(chunk):
        raise ValueError(f'{name}: 3.5 output schema not recognized; missing {cols-set(chunk)}')
    ts=pd.to_datetime(chunk['utc_minute_start'],utc=True)
    ny_day=ts.dt.tz_convert('America/New_York').dt.strftime('%Y-%m-%d')
    res=pd.DataFrame({'utc_minute_start':chunk['utc_minute_start'],
          'session_date_ny':ny_day,
          'price':pd.to_numeric(chunk['mid_close'],errors='coerce'),
          'endpoint_base':chunk['baseline_paired_non_crossed'].astype(np.uint8),
          'endpoint_strict':chunk['sensitivity_spread50_flat15_eligible'].astype(np.uint8),
          'flag_jump':chunk['mid_abs_jump_review_flag'].astype(np.uint8),
          'flag_range':0,
          'spread_gt50':chunk['spread_gt50bp_flag'].astype(np.uint8),
          'flat_age':pd.to_numeric(chunk['joint_flat_age_past_only'],errors='coerce').fillna(0).astype('int32'),
          'source_epoch':'dukascopy',
          'legacy_label_uncertain':0,
          'source_3_4_return_bp':pd.to_numeric(chunk['mid_return_1m_bp_only_adjacent_paired'],errors='coerce')})
    return res


def write(df: pd.DataFrame, path: Path, first: bool):
    # pandas CSV writer accepts gzip and append, no source mutation.
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=RuntimeWarning)
        df.to_csv(path,index=False,mode='w' if first else 'a',header=first,
                  compression={'method':'gzip','compresslevel':1},na_rep='')


def run_one(kind: str, name: str, outdir: Path, input_path: Path | None = None) -> dict:
    file = input_path or base_name(kind,name)
    if not file.is_file():
        raise FileNotFoundError(f'{name}: expected 3.4/3.5 output absent: {file}. Re-run corresponding section script.')
    return_path = outdir / f'returns_1m_{name}.csv.gz'
    gap_path = outdir / f'within_session_gaps_{name}.csv.gz'
    first_output = first_gap = True
    previous=None
    # Treat every source as its own series and do not invent a continuity
    # bridge between legacy PiTrading and modern IEX.
    counts=dict(asset=name,kind=kind,source_file=str(file),input_rows=0,
                current_eligible=0,strict_eligible_endpoints=0,
                valid_1m_returns=0,strict_valid_1m_returns=0,
                eligible_zero_returns=0,nonzero_returns=0,
                within_session_gaps=0,missing_minute_count_between_observed=0,
                new_session_boundaries=0,first_source_row=0,
                unusable_prior_endpoint=0,unusable_current_endpoint=0,
                quote_prior_endpoint_filtered=0,quote_current_endpoint_filtered=0,
                abs_gt_50bp=0,abs_gt_100bp=0,abs_gt_200bp=0,
                flagged_3_4_move=0,flagged_3_4_range=0,flagged_3_5_quote_jump=0,
                max_abs_return_bp=None,reference_return_mismatch_count=0,
                price_return_only=(kind=='ETF'),
                overnight_returns_constructed=False,
                ex_dividend_flags_constructed=False,
                historical_timestamp_label_unverified=name.endswith('LEGACY'))
    first_stamp = last_stamp = None
    for rawchunk in pd.read_csv(file,chunksize=CHUNK):
        if rawchunk.empty: continue
        chunk=prepare_batch(kind,name,rawchunk)
        # Previously processed last observation is prepended ONLY for calculations.
        frame = pd.concat([previous,chunk],ignore_index=True) if previous is not None else chunk
        ns=utc_ns(frame['utc_minute_start']); sess=frame['session_date_ny'].to_numpy(dtype=str)
        price=frame['price'].to_numpy(dtype=np.float64)
        base=frame['endpoint_base'].to_numpy(dtype=bool)
        strict=frame['endpoint_strict'].to_numpy(dtype=bool)
        st=calculate_step(ns,sess,price,base,strict)
        offset=int(previous is not None)
        # Compare with previously computed causal diagnostic from the same input.
        ref=frame['source_3_4_return_bp'].to_numpy(dtype=float)
        both=np.isfinite(ref[offset:]) & st['baseline'][offset:]
        if both.any():
            mismatch = np.abs(ref[offset:][both] - st['ret'][offset:][both]*10000)>0.0003
            counts['reference_return_mismatch_count']+=int(mismatch.sum())
            if mismatch.any():
                raise AssertionError(f'{name}: 3.4/3.5 reference log returns disagree')
        # 3.4 ETF reference must exist exactly when eligible if there is a prior bar;
        # 3.5 quote source used rounded bp and is also consistent.
        if (np.isfinite(ref[offset:]) != st['baseline'][offset:]).any():
            raise AssertionError(f'{name}: 3.4/3.5 eligibility differs from Section 3.6')
        out = pd.DataFrame({
            'utc_minute_start':frame['utc_minute_start'].iloc[offset:].to_numpy(),
            'available_utc_assuming_start_label':pd.to_datetime(ns[offset:]+MINUTE_NS,unit='ns',utc=True).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'session_date_ny':sess[offset:], 'source_epoch':frame['source_epoch'].iloc[offset:].to_numpy(),
            'price_type':'ETF_CLOSE_PRICE' if kind=='ETF' else 'INDICATIVE_PAIRED_CLOSE_MIDPOINT',
            'endpoint_price':price[offset:],
            'endpoint_eligible_baseline':st['endpoint_base'][offset:].astype('uint8'),
            'endpoint_eligible_strict':st['endpoint_strict'][offset:].astype('uint8'),
            'elapsed_minutes_from_previous_input_row_same_session':st['elapsed'][offset:],
            'return_status':st['status'][offset:],
            'return_1m_eligible_baseline':st['baseline'][offset:].astype('uint8'),
            'log_return_1m':st['ret'][offset:],
            'log_return_1m_bp':st['ret'][offset:]*10000,
            'return_1m_eligible_strict':st['strict'][offset:].astype('uint8'),
            'log_return_1m_strict':st['ret_strict'][offset:],
            'log_return_1m_strict_bp':st['ret_strict'][offset:]*10000,
            'zero_log_return_observed_1m':(st['baseline'][offset:]&(st['ret'][offset:]==0)).astype('uint8'),
            'candidate_extreme_move_flag':frame['flag_jump'].iloc[offset:].to_numpy(dtype=np.uint8),
            'candidate_large_bar_range_flag':frame['flag_range'].iloc[offset:].to_numpy(dtype=np.uint8),
            'spread_gt50bp_flag':frame['spread_gt50'].iloc[offset:].to_numpy(dtype=np.uint8),
            'joint_flat_age_past_only':frame['flat_age'].iloc[offset:].to_numpy(dtype=np.int32),
            'legacy_label_uncertain':frame['legacy_label_uncertain'].iloc[offset:].to_numpy(dtype=np.uint8),
            'overnight_return':np.zeros(len(frame)-offset,dtype=np.uint8),
            'ex_dividend_status':'PENDING_SECTION_3_8' if kind=='ETF' else 'NOT_APPLICABLE',
        })
        write(out,return_path,first_output); first_output=False
        rr=st['ret'][offset:]
        eligible=st['baseline'][offset:]
        strict_valid=st['strict'][offset:]
        counts['input_rows']+=len(out)
        counts['current_eligible']+=int(st['endpoint_base'][offset:].sum())
        counts['strict_eligible_endpoints']+=int(st['endpoint_strict'][offset:].sum())
        counts['valid_1m_returns']+=int(eligible.sum())
        counts['strict_valid_1m_returns']+=int(strict_valid.sum())
        counts['eligible_zero_returns']+=int((eligible&(rr==0)).sum())
        counts['nonzero_returns']+=int((eligible&(rr!=0)).sum())
        counts['abs_gt_50bp']+=int((np.abs(rr[eligible])*10000>50).sum())
        counts['abs_gt_100bp']+=int((np.abs(rr[eligible])*10000>100).sum())
        counts['abs_gt_200bp']+=int((np.abs(rr[eligible])*10000>200).sum())
        counts['flagged_3_4_move' if kind=='ETF' else 'flagged_3_5_quote_jump']+=int(frame['flag_jump'].iloc[offset:].sum())
        counts['flagged_3_4_range']+=int(frame['flag_range'].iloc[offset:].sum()) if kind=='ETF' else 0
        maxret=float(np.max(np.abs(rr[eligible]))*10000) if eligible.any() else 0
        if counts['max_abs_return_bp'] is None or maxret>counts['max_abs_return_bp']:
            counts['max_abs_return_bp']=maxret
        cats=st['status'][offset:]
        counts['new_session_boundaries']+=int((cats=='NEW_SESSION_NO_INTRADAY_RETURN').sum())
        counts['first_source_row']+=int((cats=='START_OF_INPUT_OR_CHUNK').sum())
        counts['unusable_prior_endpoint']+=int((cats=='PRIOR_ENDPOINT_INELIGIBLE').sum())
        counts['unusable_current_endpoint']+=int((cats=='CURRENT_ENDPOINT_INELIGIBLE').sum())
        if kind=='QUOTE':
            # Strict return can fail even with currently eligible endpoint.
            strict_here=st['endpoint_strict'][offset:]
            counts['quote_current_endpoint_filtered']+=int((st['endpoint_base'][offset:] & ~strict_here).sum())
            # Count strict attrition from either/both endpoints, not double count.
            counts['quote_prior_endpoint_filtered']+=int((eligible & strict_here & ~strict_valid).sum())
        # Gaps ledger: only physically observed rows; within session and source.
        delta=st['elapsed']; subset=np.flatnonzero((delta>=2) & st['same_session'])
        subset=subset[subset>=offset]
        if len(subset):
            gap_rows=[]
            for pos in subset:
                missing=int(delta[pos]-1)
                gap_rows.append({'asset':name,'session_date_ny':sess[pos],
                                 'last_observed_before_gap_utc':iso(ns[pos-1]),
                                 'first_observed_after_gap_utc':iso(ns[pos]),
                                 'elapsed_minutes':int(delta[pos]),
                                 'intervening_missing_minutes':missing,
                                 'source_type':kind,
                                 'note':'RETROSPECTIVE_GAP_DESCRIPTION_NOT_A_1M_RETURN'})
            gaps=pd.DataFrame(gap_rows)
            write(gaps,gap_path,first_gap);first_gap=False
            counts['within_session_gaps']+=len(gaps)
            counts['missing_minute_count_between_observed']+=int(gaps['intervening_missing_minutes'].sum())
        if first_stamp is None: first_stamp=iso(ns[offset])
        last_stamp=iso(ns[-1])
        previous=frame.iloc[[-1]].copy()
        del frame,out,st
    if counts['input_rows']==0:
        raise ValueError(f'{name}: empty source panel')
    if first_gap:
        pd.DataFrame(columns=['asset','session_date_ny','last_observed_before_gap_utc',
            'first_observed_after_gap_utc','elapsed_minutes','intervening_missing_minutes',
            'source_type','note']).to_csv(gap_path,index=False,compression='gzip')
    counts['first_minute_utc']=first_stamp
    counts['last_minute_utc']=last_stamp
    counts['returns_file']=return_path.name
    counts['within_session_gap_file']=gap_path.name
    print(f'{name}: input {counts["input_rows"]:,}, valid 1m {counts["valid_1m_returns"]:,}, '
          f'strict {counts["strict_valid_1m_returns"]:,}, within-session gaps {counts["within_session_gaps"]:,}',flush=True)
    return counts


def expected_internal_checks(summary: dict):
    # Independent historical 3.4/3.5 counts to detect accidental input changes.
    expected={
      'SPY_LEGACY':1819919,'TLT_LEGACY':1603689,'HYG_LEGACY':1260023,
      'SPY_RAW':448416,'TLT_RAW':418918,'HYG_RAW':410148,
      'GOLD':1903830,'DOLLAR':862170}
    deviations={}
    for k,v in summary.items():
        if k in expected and v['input_rows']!=expected[k]:
            deviations[k]={'expected_rows':expected[k],'observed_rows':v['input_rows']}
    if deviations:
        raise RuntimeError(f'Input row counts inconsistent with frozen 3.4/3.5 results: {deviations}')


def report_text(metrics: dict) -> str:
    rows=['# Section 3.6 — One-minute log returns and gap-aware eligibility',
          '', 'All input files were read-only. This step constructs intraday PRICE returns, not overnight or dividend total returns.',
          '', '| Dataset | Input rows | Valid 1m returns | Strict 1m | Zero returns | Gap episodes | Missing minutes between observed bars |',
          '|---|---:|---:|---:|---:|---:|---:|']
    for name,x in metrics.items():
        rows.append(f'| {name} | {x["input_rows"]:,} | {x["valid_1m_returns"]:,} | '
          f'{x["strict_valid_1m_returns"]:,} | {x["eligible_zero_returns"]:,} | '
          f'{x["within_session_gaps"]:,} | {x["missing_minute_count_between_observed"]:,} |')
    rows += ['', '## Implemented return rules',
      '- log return `r_t = ln(P_t / P_(t-1))` as unit-free decimal; `log_return_1m_bp = 10,000*r_t`.',
      '- A valid 1-minute return requires **two eligible observed endpoints**, exactly 60 seconds apart, **within one NYSE session**.',
      '- ETF price endpoint is observed bar CLOSE; quote endpoint is the mean of matched BID/ASK minute CLOSE values.',
      '- Missing minute before an otherwise valid bar leaves that minute return missing. Do not divide multi-minute changes by elapsed minutes to invent per-minute returns.',
      '- A true zero return when both adjacent prices are observed is retained; missing quote history is never assigned 0.',
      '- Candles labeled `t` have assumed earliest availability `t + 1 minute`. Historical PiTrading candle conventions remain UNVERIFIED.',
      '- ETF legacy and IEX RAW data are processed in distinct files, with no cross-source return bridge.',
      '- For quotes, strict returns require **both endpoints** to satisfy the predeclared spread <= 50bp and past-visible joint flat age < 15-minute test.',
      '- All large observed moves are retained and flagged for sensitivity, not dropped or automatically labeled errors.',
      '', '## Interpretation and limitations',
      '- These are RTH **price** log returns only; dividend distributions and ex-date event flags await 3.8.',
      '- Overnight and holiday close-to-open intervals await 3.7; do not treat the first minute of a session as an ordinary adjacent return.',
      '- Midpoints are indicative close-of-minute proxies, not verified tick-synchronous, executable prices.',
      '- Genuine market inactivity, provider omissions, fabricated flat quote candles, and dividend mechanics can remain unresolved.',
      '- Retrospective gap interval ledgers use next-observed timestamps; never use them as at-time model features.',
      '- Actual HMM/event-study sensitivity, aggregate bars and cross-asset panels belong to subsequent sections.',
      '', '## Output',
      '- `returns_1m_*.csv.gz`: observed eligible prices/returns, flags, and explicit null returns for ineligible endpoints.',
      '- `within_session_gaps_*.csv.gz`: descriptive, retrospective ledger of gaps **between observed endpoints**; not a full missingness grid.',
      '- `summary.json`: exact counts and documented return basis. Retain Section 3.3 full-grid masks for complete missing-observation flags.',
      '', '**Status:** Review self-tests, reconciliation to Section 3.4/3.5 and counts, then freeze Section 3.6.' ]
    return '\n'.join(rows)+'\n'


def run(args):
    self_tests()
    OUT.mkdir(parents=True,exist_ok=True)
    metrics={}
    kindset=[('ETF', n) for n in SOURCES_ETF]+[('QUOTE',n) for n in SOURCES_QUOTE]
    if args.only:
        kindset=[x for x in kindset if x[1] in args.only]
        if not kindset:raise ValueError('No matching assets in --only')
    for kind,name in kindset:
        print(f'Loading {name}...',flush=True)
        metrics[name]=run_one(kind,name,OUT)
    if not args.only: expected_internal_checks(metrics)
    payload=dict(section='3.6 Return calculations',definition='natural log close_t / close_(t-1)',
      return_units=['decimal','basis_points'],assume_minute_start=True,
      legacy_label_convention='UNVERIFIED',overnight_treatment='PENDING_3_7',
      dividend_total_return_treatment='PENDING_3_8',
      strict_quote_rule='two endpoints paired, spread<=50bp and past-only joint flat age<15',
      source_panels='3.4 ETF and 3.5 quote quality outputs',datasets=metrics)
    (OUT/'summary.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    (OUT/'REPORT.md').write_text(report_text(metrics),encoding='utf-8')
    print(f'SUCCESS. Results: {OUT}\nUpload REPORT.md and summary.json. Keep compressed return/gap panels locally.',flush=True)


if __name__=='__main__':
    a=argparse.ArgumentParser()
    a.add_argument('--self-test',action='store_true',help='Only run synthetic tests')
    a.add_argument('--only',nargs='*',choices=list(SOURCES_ETF)+list(SOURCES_QUOTE),
                   help='Optional diagnostic subset (all assets by default)')
    args=a.parse_args()
    if args.self_test:self_tests()
    else:run(args)
