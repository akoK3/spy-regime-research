#!/usr/bin/env python3
r"""Section 3.9 — session-anchored multi-minute aggregation and coverage testing.

Windows are built from Section 3.4 ETF observed bars and Section 3.5 quote-quality
panels, with unobserved minutes NEVER interpolated. Session opens anchor bins.

PowerShell:
    python "$HOME\Downloads\section3_9_timeframe_aggregation.py"
    python "$HOME\Downloads\section3_9_timeframe_aggregation.py" --self-test

Dependencies: numpy, pandas, pandas_market_calendars OR exchange_calendars.
Inputs (must exist):
  Downloads/section3_4_etf_results/etf_observed_{ticker}_{epoch}.csv.gz
  Downloads/section3_5_quote_quality_results/quote_quality_rth_{asset}.csv.gz
Outputs: Downloads/section3_9_aggregation_results/

Analysis rules:
* Primary remains native 1-minute; 2,3,4,5,10,15m are prespecified alternatives.
* A k-minute return is defined ONLY between two consecutive exactly timed window-
  end CLOSE observations in the SAME exchange session. Missing interior minutes
  may exist: such observations are labeled endpoint-only, not complete.
* The strict return requires BOTH entire windows complete. Quote strict additionally
  requires every constituent minute to meet the predeclared spread/flat screen.
* All reported k returns are k-clock-minute log returns; no bridging session gaps,
  no price interpolation and no ex-dividend/overnight adjustment in this step.
* Windows with fewer scheduled minutes than k (session tail, early close) are
  preserved with a partial-time label but cannot generate a nominal k return.
* The legacy start-of-minute clock assumption remains UNVERIFIED.
* Source epochs are never joined here, and no HMM outcomes choose a frequency.
"""
from __future__ import annotations
import argparse
import json
import math
import warnings
from pathlib import Path
import numpy as np
import pandas as pd

MIN = 60_000_000_000
FREQUENCIES = (2, 3, 4, 5, 10, 15)
ETF_NAMES = ('SPY_LEGACY', 'TLT_LEGACY', 'HYG_LEGACY', 'SPY_RAW', 'TLT_RAW', 'HYG_RAW')
QUOTE_NAMES = ('GOLD', 'DOLLAR')
DL = Path.home() / 'Downloads'
ETF_DIR = DL / 'section3_4_etf_results'
QUOTE_DIR = DL / 'section3_5_quote_quality_results'
OUT = DL / 'section3_9_aggregation_results'


def schedule():
    try:
        import pandas_market_calendars as mcal
        s = mcal.get_calendar('XNYS').schedule(start_date='2002-12-30',end_date='2026-10-14')
    except ImportError:
        try:
            import exchange_calendars as ec
            s = ec.get_calendar('XNYS', start='2002-12-30',end='2026-10-14').schedule.rename(
                columns={'open':'market_open','close':'market_close'})
        except ImportError as err:
            raise SystemExit('Install: python -m pip install pandas_market_calendars') from err
    starts = pd.DatetimeIndex(s['market_open']).asi8
    ends = pd.DatetimeIndex(s['market_close']).asi8
    if not np.all((ends-starts)%MIN==0):
        raise ValueError('Exchange calendar contains non-integer-minute sessions')
    return starts, ends, s.index.strftime('%Y-%m-%d').to_numpy()


def ns_from_utc(series):
    v = pd.to_datetime(series,utc=True,errors='raise')
    if v.isna().any(): raise ValueError('Timestamp NaT')
    return v.astype('int64').to_numpy(dtype=np.int64)


def stamp(int_ns):
    return pd.to_datetime(int_ns, unit='ns',utc=True).strftime('%Y-%m-%dT%H:%M:%SZ')


def load_one(name):
    if name in ETF_NAMES:
        file=ETF_DIR / f'etf_observed_{name}.csv.gz'
        required=['utc_minute_start','session_date_ny','source_epoch',
                  'Open','High','Low','Close','Volume','review_move_gt_200bp','review_range_gt_200bp']
        kind='ETF'
    else:
        file=QUOTE_DIR / f'quote_quality_rth_{name}.csv.gz'
        required=['utc_minute_start','mid_close','baseline_paired_non_crossed',
                  'sensitivity_spread50_flat15_eligible','spread_gt50bp_flag',
                  'joint_flat_age_past_only','mid_abs_jump_review_flag','spread_bp']
        kind='QUOTE'
    if not file.is_file():
        raise FileNotFoundError(f'Missing prerequisite {file}. Run Section 3.4 or 3.5 first.')
    header=pd.read_csv(file,nrows=0)
    absent=set(required)-set(header.columns)
    if absent:raise ValueError(f'{name}: missing columns: {absent}')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        df=pd.read_csv(file,usecols=required)
    if df.empty:raise ValueError(f'{name}: empty source panel')
    timestamps=ns_from_utc(df['utc_minute_start'])
    if len(timestamps)>1 and not np.all(np.diff(timestamps)==MIN if kind=='QUOTE' else np.diff(timestamps)>0):
        # Quote full XNYS RTH panel spans overnight: stricly ordered, not continuous.
        if not np.all(np.diff(timestamps)>0):
            raise ValueError(f'{name}: non-strict chronology')
    if kind=='ETF':
        target='pitrading' if name.endswith('_LEGACY') else 'iex'
        if not (df['source_epoch'].astype(str)==target).all():
            raise ValueError(f'{name}: mixed source provenance')
        numeric=df[['Open','High','Low','Close','Volume']].to_numpy(float)
        o,h,l,c,v = numeric.T
        if not (np.isfinite(numeric).all() and (o>0).all() and (l>0).all()
                and (h>=np.maximum(o,c)).all() and (l<=np.minimum(o,c)).all()
                and (v>=0).all()):
            raise ValueError(f'{name}: invalid OHLCV in 3.4 panel')
        obs=np.ones(len(df),dtype=bool)
        strict=obs.copy()
        input_data=dict(open=o,high=h,low=l,close=c,volume=v,
            any_warn=(df['review_move_gt_200bp'].to_numpy(bool)
                     | df['review_range_gt_200bp'].to_numpy(bool)))
    else:
        c=pd.to_numeric(df['mid_close'],errors='coerce').to_numpy(float)
        obs=(df['baseline_paired_non_crossed'].to_numpy(bool)&np.isfinite(c)&(c>0))
        strict=obs & df['sensitivity_spread50_flat15_eligible'].to_numpy(bool)
        input_data=dict(close=np.where(obs,c,np.nan),
            spread=pd.to_numeric(df['spread_bp'],errors='coerce').to_numpy(float),
            any_warn=(df['spread_gt50bp_flag'].to_numpy(bool) |
                (df['joint_flat_age_past_only'].to_numpy(float)>=15) |
                df['mid_abs_jump_review_flag'].to_numpy(bool)))
    return kind,file,timestamps,obs,strict,input_data


def build_one(k, name, kind, ts, obs, strict, x, cal_open, cal_close, cal_day,
              *, first_label=None, last_label=None):
    """Return observed windows and diagnostic summary; complete sessions only in denominator.

    Each group has a nominal scheduled window that may be short at session end.
    No interpolation, no ffill and no k-minute return if endpoint is missing.
    """
    if len(ts)!=len(obs):raise ValueError('Mismatched row counts')
    if first_label is None:first_label=int(ts[0])
    if last_label is None:last_label=int(ts[-1])
    sid=np.searchsorted(cal_open,ts,side='right')-1
    if ((sid<0)|(sid>=len(cal_open))).any():
        raise ValueError(f'{name}: timestamp outside schedule')
    if ((ts<cal_open[sid])|(ts>=cal_close[sid])|((ts-cal_open[sid])%MIN!=0)).any():
        raise ValueError(f'{name}: minute outside XNYS session or misaligned')
    pos=((ts-cal_open[sid])//MIN).astype(np.int64)
    wno=pos//k
    wstart=cal_open[sid]+wno*k*MIN
    wend=np.minimum(wstart+k*MIN,cal_close[sid])
    # Frame can include both observed and not paired quote labels; only observed
    # values contribute to OHLCV or return endpoint.
    frame=pd.DataFrame({'session_i':sid,'window_start_ns':wstart,'window_end_ns':wend,
        'minute_ns':ts, 'minute_pos':pos, 'obs':obs.astype(np.uint8),
        'strict':strict.astype(np.uint8), 'close':x['close'],
        'warn':x['any_warn'].astype(np.uint8)})
    if kind=='ETF':
        for col in ('open','high','low','volume'):
            frame[col]=x[col]
    else:
        frame['spread']=x['spread']
    # Enforce exact dataset span, excluding *truncated* leading/trailing windows.
    # First minute may occur midday at inception (HYG); avoid inventing missing
    # pre-inception windows. Last source day similarly.
    frame=frame[(frame.window_start_ns>=first_label)&(frame.window_end_ns<=last_label+MIN)].copy()
    if frame.empty:
        return pd.DataFrame(),{'asset':name,'frequency_min':k,'scheduled_windows':0}
    # Group only by sessions and starting instant. Input chronology is strictly
    # increasing, hence observed first/last are chronological.
    good=frame[frame.obs==1]
    keys=['session_i','window_start_ns']
    grouped=frame.groupby(keys,sort=True,observed=True)
    cnt=grouped.agg(window_end_ns=('window_end_ns','first'),
        eligible_minutes=('obs','sum'), strict_minutes=('strict','sum'),
        warning_minutes=('warn','sum')).reset_index()
    if not good.empty:
        g=good.groupby(keys,sort=True,observed=True)
        if kind=='ETF':
            val=g.agg(agg_open=('open','first'),agg_high=('high','max'),
                agg_low=('low','min'),agg_close=('close','last'),
                observed_volume_sum=('volume','sum'),
                last_observed_minute_ns=('minute_ns','last'),
                first_observed_minute_ns=('minute_ns','first')).reset_index()
        else:
            val=g.agg(agg_first_midpoint_sample=('close','first'),
                agg_min_midpoint_sample=('close','min'),
                agg_max_midpoint_sample=('close','max'),
                agg_close=('close','last'),max_recorded_spread_bp=('spread','max'),
                last_observed_minute_ns=('minute_ns','last'),
                first_observed_minute_ns=('minute_ns','first')).reset_index()
        cnt=cnt.merge(val,on=keys,how='left',validate='one_to_one',sort=False)
    num=(cnt.window_end_ns-cnt.window_start_ns)//MIN
    cnt['scheduled_minutes']=num.astype('int16')
    cnt['full_duration_window']=num==k
    cnt['complete_data_window']=(cnt.eligible_minutes==num)
    cnt['strict_data_window']=(cnt.strict_minutes==num)
    cnt['last_slot_observed']=(cnt.eligible_minutes>0)&(
        cnt.last_observed_minute_ns==cnt.window_end_ns-MIN)
    cnt['first_slot_observed']=(cnt.eligible_minutes>0)&(
        cnt.first_observed_minute_ns==cnt.window_start_ns)
    cnt['missing_constituent_minutes']=cnt.scheduled_minutes-cnt.eligible_minutes
    cnt['observed_fraction']=cnt.eligible_minutes/cnt.scheduled_minutes
    # Do not let any current window use a prior session's last candle.
    prev_same=(cnt.session_i.to_numpy()[1:]==cnt.session_i.to_numpy()[:-1])
    starts=cnt.window_start_ns.to_numpy(np.int64)
    prev_contig=np.zeros(len(cnt),dtype=bool)
    prev_contig[1:]=prev_same & ((starts[1:]-starts[:-1])==k*MIN)
    end=cnt.last_slot_observed.to_numpy(bool)
    full=cnt.full_duration_window.to_numpy(bool)
    complete=cnt.complete_data_window.to_numpy(bool)
    stricter=cnt.strict_data_window.to_numpy(bool)
    base=np.zeros(len(cnt),dtype=bool)
    full_mask=np.zeros(len(cnt),dtype=bool)
    strict_mask=np.zeros(len(cnt),dtype=bool)
    if len(cnt)>1:
        base[1:]=prev_contig[1:]&full[1:]&full[:-1]&end[1:]&end[:-1]
        full_mask[1:]=base[1:]&complete[1:]&complete[:-1]
        strict_mask[1:]=full_mask[1:]&stricter[1:]&stricter[:-1]
    # Check that return for k windows has exactly k minutes elapsed between
    # actual recorded close endpoints, not merely between guessed window labels.
    ci=np.where(base)[0]
    if len(ci) and not (cnt.last_observed_minute_ns.to_numpy()[ci]-
        cnt.last_observed_minute_ns.to_numpy()[ci-1]==k*MIN).all():
        raise AssertionError('Non-k elapsed time for k-minute return')
    close=cnt.agg_close.to_numpy(float)
    ret=np.full(len(cnt),np.nan)
    if len(ci):ret[ci]=np.log(close[ci]/close[ci-1])
    cnt['endpoint_anchored_log_return_km']=ret
    cnt['endpoint_anchored_log_return_km_bp']=ret*10_000
    cnt['complete_only_log_return_km']=np.where(full_mask,ret,np.nan)
    cnt['strict_log_return_km']=np.where(strict_mask,ret,np.nan)
    cnt['endpoint_anchored_eligible']=base
    cnt['complete_only_eligible']=full_mask
    cnt['strict_eligible']=strict_mask
    cnt['window_start_utc']=stamp(cnt.window_start_ns.to_numpy(np.int64))
    cnt['window_end_available_utc_assuming_start_labels']=stamp(cnt.window_end_ns.to_numpy(np.int64))
    cnt['session_date_ny']=cal_day[cnt.session_i.to_numpy(np.int64)]
    cnt['source_epoch']='pitrading' if name.endswith('_LEGACY') else ('iex' if name.endswith('_RAW') else 'dukascopy')
    cnt['historical_candle_time_unverified']=name.endswith('_LEGACY')
    cnt['asset']=name
    cnt['frequency_min']=k
    # Complete nominal windows between first and last in-scope source timestamps,
    # including those with zero records (these require the calendar).
    session_id=np.arange(len(cal_open))
    full_scheduled=(cal_close-cal_open)//MIN//k
    # Existing input span at window precision: window must be wholly included.
    total_full=0
    eligible_slot_positions=0
    yr_items=[]
    for s in session_id:
        count=int(full_scheduled[s]);
        if count<=0:continue
        starts_s=cal_open[s]+np.arange(count,dtype=np.int64)*k*MIN
        in_scope=(starts_s>=first_label)&(starts_s+k*MIN<=last_label+MIN)
        m=int(in_scope.sum())
        total_full+=m
        # Valid pairs require both consecutive full scheduled windows in scope
        if m>=2:eligible_slot_positions+=m-1
    full_cnt=cnt[cnt.full_duration_window]
    good_bar=int(((cnt.complete_data_window)&(cnt.full_duration_window)).sum())
    observed_full=int(((cnt.eligible_minutes>0)&(cnt.full_duration_window)).sum())
    partial_duration=int((~cnt.full_duration_window).sum())
    if total_full < len(full_cnt):
        raise AssertionError(f'{name} {k}: more observed full windows than scheduled')
    if np.any(strict_mask & ~full_mask) or np.any(full_mask & ~base):
        raise AssertionError('Eligibility relation violated')
    stats={
        'asset':name,'frequency_min':k,'scheduled_full_windows_in_source_span':total_full,
        'full_windows_with_at_least_one_observation':observed_full,
        'full_windows_complete_all_minutes':good_bar,
        'full_windows_missing_entirely':total_full-observed_full,
        'full_windows_incomplete_but_observed':observed_full-good_bar,
        'non_k_session_tail_windows_preserved':partial_duration,
        'candidate_consecutive_k_return_positions':eligible_slot_positions,
        'endpoint_anchored_k_returns':int(base.sum()),
        'complete_only_k_returns':int(full_mask.sum()),
        'strict_k_returns':int(strict_mask.sum()),
        'endpoint_anchored_coverage_pct':100*float(base.sum())/eligible_slot_positions if eligible_slot_positions else None,
        'complete_only_coverage_pct':100*float(full_mask.sum())/eligible_slot_positions if eligible_slot_positions else None,
        'full_window_observed_coverage_pct':100*good_bar/total_full if total_full else None,
        'strict_window_coverage_pct':100*int(((cnt.strict_data_window)&cnt.full_duration_window).sum())/total_full if total_full else None,
        'flags_for_interpretation':'Endpoint-only k returns can bridge missing INTERIOR minute records; never call them complete data.',
    }
    # Output all observed/incomplete windows, not zero-record windows (counted
    # above using the calendar). Include the missingness ledger from 3.3 later.
    cnt=cnt[cnt.eligible_minutes>0].copy()
    return cnt,stats


def unit_tests():
    base=pd.Timestamp('2024-11-29T14:30:00Z').value
    # Simulated NYSE half-session: 4-minute day for simple checks
    cal_o=np.array([base,base+3*24*60*MIN],dtype=np.int64)
    cal_c=cal_o+4*MIN
    day=np.array(['2024-11-29','2024-12-02'])
    # Day 1 minute 1 absent: k2 first bin incomplete, second bin complete;
    # no complete-only k2 return, endpoint-only still possible if minute 1 missing?
    # Require exact end minute of the first bin: missing at index1 => no base.
    ts=np.array([base,base+2*MIN,base+3*MIN],dtype=np.int64)
    x={'open':np.array([100.,102.,103.]),'high':np.array([101.,103.,104.]),
       'low':np.array([99.,101.,102.]),'close':np.array([100.,102.,103.]),
       'volume':np.array([5.,7.,9.]),'any_warn':np.zeros(3,bool)}
    out,s=build_one(2,'SPY_RAW','ETF',ts,np.ones(3,bool),np.ones(3,bool),x,
                    cal_o,cal_c,day)
    assert s['scheduled_full_windows_in_source_span']==2
    assert s['full_windows_complete_all_minutes']==1
    assert s['endpoint_anchored_k_returns']==0
    assert out.observed_volume_sum.sum()==21
    # Both endpoints exist but interior is absent: valid k-clock-minute return
    # (not complete-only), with explicit incomplete window.
    ts2=np.array([base,base+MIN,base+3*MIN],dtype=np.int64)
    x2={key:val[[0,1,2]] for key,val in x.items()}
    out2,s2=build_one(2,'SPY_RAW','ETF',ts2,np.ones(3,bool),np.ones(3,bool),x2,
                      cal_o,cal_c,day)
    assert s2['endpoint_anchored_k_returns']==1,s2
    assert s2['complete_only_k_returns']==0
    assert out2.endpoint_anchored_log_return_km.notna().sum()==1
    # No return ever between distinct sessions.
    ts3=np.array([base+MIN,base+3*MIN,cal_o[1]+MIN,cal_o[1]+3*MIN])
    x3={'close':np.array([100.,101.,102.,103.]),'open':np.array([100.,101.,102.,103.]),
        'high':np.array([100.,101.,102.,103.]),'low':np.array([100.,101.,102.,103.]),
        'volume':np.ones(4),'any_warn':np.zeros(4,bool)}
    out3,s3=build_one(2,'TLT_LEGACY','ETF',ts3,np.ones(4,bool),np.ones(4,bool),x3,
                      cal_o,cal_c,day)
    assert not (out3.endpoint_anchored_log_return_km.notna() &
        (out3.session_date_ny=='2024-12-02') & (out3.window_start_ns==cal_o[1])).any()
    # Quote cannot use unpaired midpoint or spurious zero price, and a strict
    # stale endpoint excludes the strict variant only.
    qts=np.array([base,base+MIN,base+2*MIN,base+3*MIN])
    qc=np.array([99.,100.,np.nan,104.]); b=np.array([1,1,0,1],dtype=bool)
    qx={'close':qc,'spread':np.array([2.,2.,np.nan,2.]),'any_warn':np.zeros(4,bool)}
    qr,qs=build_one(2,'GOLD','QUOTE',qts,b,np.array([1,0,0,1],bool),qx,
                     cal_o,cal_c,day)
    assert qs['endpoint_anchored_k_returns']==1
    assert qs['strict_k_returns']==0
    assert qs['complete_only_k_returns']==0
    # A truncated session tail must not be a nominal k-minute return.
    ts4=np.array([base+i*MIN for i in range(4)],dtype=np.int64)
    x4={'close':np.arange(100,104,dtype=float),'open':np.arange(100,104,dtype=float),
        'high':np.arange(100,104,dtype=float),'low':np.arange(100,104,dtype=float),
        'volume':np.ones(4),'any_warn':np.zeros(4,bool)}
    tail,tail_s=build_one(3,'SPY_RAW','ETF',ts4,np.ones(4,bool),np.ones(4,bool),x4,
                    cal_o,cal_c,day)
    assert tail_s['non_k_session_tail_windows_preserved']==1
    assert tail_s['endpoint_anchored_k_returns']==0
    # Future edits must not change an earlier window's return.
    ts5=np.array([base+i*MIN for i in range(4)],dtype=np.int64)
    future={key:val.copy() for key,val in x4.items()};future['close'][-1]=1000.
    a,asum=build_one(2,'SPY_RAW','ETF',ts5,np.ones(4,bool),np.ones(4,bool),x4,cal_o,cal_c,day)
    b,bsum=build_one(2,'SPY_RAW','ETF',ts5,np.ones(4,bool),np.ones(4,bool),future,cal_o,cal_c,day)
    assert a.agg_close.iloc[0]==b.agg_close.iloc[0]
    assert a.endpoint_anchored_log_return_km.isna().iloc[0]
    print('SELF-TEST PASS: session anchor, missing interior, quote sides, strict flags, early-tail and no cross-session returns',flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    unit_tests()
    if args.self_test:return
    cal_o,cal_c,days=schedule()
    OUT.mkdir(parents=True,exist_ok=True)
    result={'section':'3.9 timeframe aggregation','primary':'1-minute','alternatives_minutes':list(FREQUENCIES),
        'clock':'XNYS RTH exchange open-anchored in UTC','no_imputation':True,
        'ret_k_definition':'log(current exact last-minute CLOSE / prior exact last-minute CLOSE), at k minutes elapsed, within same session',
        'tiers':{'endpoint':'exact k-minute window end points present; may have interior gaps',
            'complete':'endpoint return AND all minute observations in BOTH k windows present',
            'strict':'complete AND all constituent quotes satisfy Section 3.5 spread/flat rule (ETF same as complete)'},
        'legacy_time_uncertainty':'Start label assumed; vendor clock unverified',
        'overnight_and_exdates':'Not joined or altered in 3.9; Sections 3.7/3.8 remain separate',
        'no_model_frequency_selection':True,'dataset':{}}
    brief=[]
    for name in (*ETF_NAMES,*QUOTE_NAMES):
        kind,file,ts,obs,strict,x=load_one(name)
        print(f'Loading {name}: {len(ts):,} minute labels, {int(obs.sum()):,} eligible...',flush=True)
        ds={}
        for k in FREQUENCIES:
            frame,s=build_one(k,name,kind,ts,obs,strict,x,cal_o,cal_c,days)
            dst=OUT / f'bars_{k}m_{name}.csv.gz'
            if not frame.empty:
                # Keep outputs for 3.10 panels, notably incomplete bar indicators.
                col_drop=['session_i','window_start_ns','window_end_ns','last_observed_minute_ns','first_observed_minute_ns']
                frame.drop(columns=[c for c in col_drop if c in frame.columns]).to_csv(
                    dst,index=False,compression={'method':'gzip','compresslevel':1},na_rep='')
            else:pd.DataFrame().to_csv(dst,index=False,compression='gzip')
            s['file']=str(dst)
            ds[str(k)]=s
            brief.append(s)
            print(f'  {k:2d}m: complete {s["full_windows_complete_all_minutes"]:,}/'
                  f'{s["scheduled_full_windows_in_source_span"]:,} windows; '
                  f'endpoint returns {s["endpoint_anchored_k_returns"]:,}, '
                  f'complete returns {s["complete_only_k_returns"]:,}',flush=True)
        result['dataset'][name]={'kind':kind,'input_file':str(file),'source_minutes':len(ts),
                                'source_eligible_minutes':int(obs.sum()),'frequency':ds}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    pd.DataFrame(brief).to_csv(OUT/'frequency_comparison.csv',index=False)
    report=['# Section 3.9 — Timeframe aggregation','',
        '**Primary remains 1 minute.** Coarser windows (2,3,4,5,10,15m) are alternatives.',
        '', 'A return that uses two exactly timed window-end prices can skip missing '
        'interior source minutes, **but does not restore missing prices**. Complete-only '
        'requires all constituent source minutes in both adjacent windows.',
        '', '| Dataset | Minutes | Scheduled full bars | Complete bars | Endpoint k returns | Complete k returns | Endpoint coverage | Complete coverage |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for s in brief:
        a=s['endpoint_anchored_coverage_pct'];b=s['complete_only_coverage_pct']
        pct=lambda v: f'{v:.2f}%' if v is not None else 'n/a'
        report.append(f'| {s["asset"]} | {s["frequency_min"]} | {s["scheduled_full_windows_in_source_span"]:,} | '
          f'{s["full_windows_complete_all_minutes"]:,} | {s["endpoint_anchored_k_returns"]:,} | '
          f'{s["complete_only_k_returns"]:,} | {pct(a)} | {pct(b)} |')
    report.extend(['', '## Rules and limitations',
        '- Session-anchored bins in UTC; holidays, DST and half-days from XNYS.',
        '- ETF OHLCV use only present observations; partial bars have explicit observed minute counts. '
        'Volume is sum of available source volumes (incomplete if any minute absent).',
        '- Quote aggregate is a **sampled minute-close midpoint proxy**; min/max are not actual trade OHLC. '
        'Strict quote variants require predeclared spread/flat-age eligibility.',
        '- A nominal k-minute log return requires two exactly k-minute-separated window-end closes '
        'inside the same session. No daily, overnight, provider-epoch, or short-tail bridging.',
        '- Window end = earliest assumed availability, conditional on unverified historical PiTrading candle labeling.',
        '- No corporate-action adjustments are introduced here; primary remains saved native 1-minute returns.',
        '- **Not decided here:** whether k-minute aggregation actually helps HMM/event studies. That requires model-blind '
        'quality comparisons (Section 3.12) and later outcome robustness.',
        '- Fully empty windows are counted using the calendar but not written as empty rows in observed bars; '
        'use Section 3.3 complete masks for those.',
        '', '## Artifacts',
        '- `bars_{k}m_{name}.csv.gz` includes OHLCV or midpoint samples, completeness/quality flags, exact endpoint k returns.',
        '- `frequency_comparison.csv` contains the comparable full-grid and eligibility counts.',
        '- `summary.json` records methodology, counts and the input files.',
        '', '**Next:** Review coverage and partial-bar consequences, then freeze 3.9 and construct pairwise panels in 3.10.'])
    (OUT/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print(f'SUCCESS. Upload REPORT.md and summary.json from {OUT}; keep compressed bar files locally.',flush=True)


if __name__=='__main__':
    main()
