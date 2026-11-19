#!/usr/bin/env python3
r"""Section 3.7 — exchange-close to next-session-open return construction.

Run from PowerShell:
    python "$HOME\Downloads\section3_7_overnight_handling.py"
Optional fast tests:
    python "$HOME\Downloads\section3_7_overnight_handling.py" --self-test

Requires pandas, numpy, pandas_market_calendars. Reads existing section 3.4 ETF
panels and original Dukascopy bid/ask files. NEVER modifies originals.

Method:
  - ETF: previous XNYS final minute bar CLOSE to next session's first
    scheduled minute bar OPEN, only if both EXACT bars exist.
  - Gold/dollar: midpoint of both sides' minute CLOSE at preceding XNYS
    last-minute label versus both sides' minute OPEN at next XNYS opening label.
  - No invented minutes, replacement endpoints, source-epoch bridges, or
    dividend adjustments. Keep overnight distinct from intraday 1m returns.
  - Strict quote column is *spread-only* (<=50bp at both endpoints): it is NOT
    the 3.5 intraday strict screen, because opening-minute flat-age known at
    9:31 would be future information at 9:30.
  - Endpoints are approximate auction/last-trade proxies; a 9:30 candle OPEN
    may occur after 9:30. All constructed overnight values are assigned a
    conservative availability timestamp of next scheduled open + 1 minute.
  - Historical PiTrading minute start labeling unverified; provisional results.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

HOME=Path.home()
DL=HOME/'Downloads'
ROOT=HOME/'OneDrive'/'Desktop'/'data'/'raw'
ETF_DIR=DL/'section3_4_etf_results'
OUT=DL/'section3_7_overnight_results'
MIN=60_000_000_000
CHUNK=300_000
ETF_NAMES=('SPY_LEGACY','TLT_LEGACY','HYG_LEGACY','SPY_RAW','TLT_RAW','HYG_RAW')
Q_FILES={
  'GOLD':{'bid':ROOT/'xauusd-m1-bid-2007-04-11-2026-10-02 - Copy.csv',
          'ask':ROOT/'xauusd-m1-ask-2007-04-11-2026-10-02.csv'},
  'DOLLAR':{'bid':ROOT/'dollaridxusd-m1-bid-2017-12-01-2026-10-02.csv',
            'ask':ROOT/'dollaridxusd-m1-ask-2017-12-01-2026-10-02.csv'}
}

def ns(x):
    return pd.to_datetime(x,utc=True).astype('int64').to_numpy(dtype=np.int64)

def utc(x):
    return pd.to_datetime(x,unit='ns',utc=True).strftime('%Y-%m-%dT%H:%M:%SZ')

def schedule():
    try:
        import pandas_market_calendars as pmc
    except ImportError as e:
        raise SystemExit('Missing package: python -m pip install pandas_market_calendars') from e
    sch=pmc.get_calendar('XNYS').schedule(start_date='2002-12-30',end_date='2026-10-14')
    d=sch.index.strftime('%Y-%m-%d').to_numpy()
    opening=pd.DatetimeIndex(sch['market_open']).asi8
    closing=pd.DatetimeIndex(sch['market_close']).asi8
    assert np.all((closing-opening)%MIN==0)
    assert np.all(closing>opening)
    df=pd.DataFrame({'session':d,'open_ns':opening,'close_ns':closing,
                     'last_label_ns':closing-MIN})
    return df

def pairs(sch):
    """Each record is ONE adjacent XNYS session pair, not adjacent file rows."""
    prv=sch.iloc[:-1].reset_index(drop=True)
    nxt=sch.iloc[1:].reset_index(drop=True)
    prev_label=prv.last_label_ns.to_numpy(np.int64)
    next_label=nxt.open_ns.to_numpy(np.int64)
    prev_close=prv.close_ns.to_numpy(np.int64)
    days=(pd.to_datetime(nxt.session).to_numpy(dtype='datetime64[D]')-
          pd.to_datetime(prv.session).to_numpy(dtype='datetime64[D]')).astype('timedelta64[D]').astype(int)
    weekday=pd.to_datetime(prv.session).dt.dayofweek.to_numpy()
    break_kind=np.where(days==1,'WEEKNIGHT',
                 np.where((days==3)&(weekday==4),'WEEKEND','HOLIDAY_OR_EXTENDED_BREAK'))
    nyc=pd.to_datetime(prev_close,utc=True).tz_convert('America/New_York')
    early=(nyc.hour<16)
    return pd.DataFrame({
      'previous_session':prv.session.to_numpy(), 'session':nxt.session.to_numpy(),
      'prior_close_utc':utc(prev_close), 'next_open_utc':utc(next_label),
      'prior_close_label_utc':utc(prev_label),
      'prior_close_label_ns':prev_label,'next_open_label_ns':next_label,
      'prior_close_ns':prev_close,'next_open_ns':next_label,
      'elapsed_minutes':((next_label-prev_close)//MIN).astype(int),
      'calendar_days_between':days,'break_kind':break_kind,
      'prior_early_close':np.asarray(early,dtype=np.uint8),
      'conservative_available_utc':utc(next_label+MIN),
      'ex_dividend_status':'NOT_CHECKED_SECTION_3_8',
    })

def fetch_etf_edges(name, sch):
    path=ETF_DIR/f'etf_observed_{name}.csv.gz'
    if not path.is_file():
        raise FileNotFoundError(f'{name}: missing Section 3.4 file {path}')
    starts=sch.open_ns.to_numpy(np.int64)
    ends=sch.last_label_ns.to_numpy(np.int64)
    target=np.unique(np.r_[starts,ends]);target.sort()
    found={}; earliest=latest=None; last_seen=None;rows=0
    wanted=['utc_minute_start','session_date_ny','Open','Close','source_epoch']
    expectation='pitrading' if name.endswith('_LEGACY') else 'iex'
    for ch in pd.read_csv(path,usecols=wanted,chunksize=CHUNK):
        dates=ns(ch.utc_minute_start)
        if len(dates)>1 and np.any(np.diff(dates)<=0): raise ValueError(f'{name}: duplicate or unordered timestamps')
        if last_seen is not None and dates[0]<=last_seen: raise ValueError(f'{name}: chunk order error')
        if (ch.source_epoch.astype(str)!=expectation).any(): raise ValueError(f'{name}: epoch inconsistent')
        rows+=len(ch);last_seen=int(dates[-1]);earliest=int(dates[0]) if earliest is None else earliest;latest=int(dates[-1])
        p=np.searchsorted(target,dates)
        yes=p<len(target)
        take=yes.copy();take[yes]=target[p[yes]]==dates[yes]
        indices=np.flatnonzero(take)
        for i in indices:
            stamp=int(dates[i])
            if stamp in found: raise ValueError(f'{name}: duplicate endpoint {stamp}')
            o=float(ch.Open.iloc[i]);c=float(ch.Close.iloc[i])
            if not (np.isfinite(o) and o>0 and np.isfinite(c) and c>0):raise ValueError(f'{name}: invalid retained OHLC endpoint')
            found[stamp]=(o,c)
    if not found: raise ValueError(f'{name}: no XNYS endpoint bars present')
    return found, {'source_file':str(path),'observed_rows':rows,'earliest_label_utc':utc([earliest])[0],
                   'latest_label_utc':utc([latest])[0],'found_endpoint_labels':len(found)},earliest,latest

def quote_side_edges(path, target):
    if not path.is_file():raise FileNotFoundError(f'Missing quote source: {path}')
    seen={};first=last=None; total=0
    for c in pd.read_csv(path,usecols=['timestamp','open','high','low','close'],chunksize=CHUNK):
        ms=pd.to_numeric(c.timestamp,errors='coerce')
        if ms.isna().any() or (ms<100_000_000_000).any() or (ms>100_000_000_000_000).any() or (ms%60_000!=0).any():
            raise ValueError(f'{path.name}: invalid UTC timestamp unit')
        t=ms.astype('int64').to_numpy()*1_000_000
        if len(t)>1 and (np.diff(t)<=0).any():raise ValueError(f'{path.name}: timestamps unordered')
        if last is not None and t[0]<=last:raise ValueError(f'{path.name}: bad cross-chunk ordering')
        first=int(t[0]) if first is None else first;last=int(t[-1]);total+=len(t)
        p=np.searchsorted(target,t)
        mask=p<len(target)
        ix=np.flatnonzero(mask)
        ix=ix[target[p[ix]]==t[ix]]
        for i in ix:
            stamp=int(t[i]);o,h,l,cl=map(float,(c.open.iloc[i],c.high.iloc[i],c.low.iloc[i],c.close.iloc[i]))
            valid=bool(np.all(np.isfinite([o,h,l,cl])) and min(o,h,l,cl)>0 and h>=max(o,cl) and l<=min(o,cl) and h>=l)
            if stamp in seen:raise ValueError(f'{path.name}: duplicate target timestamp')
            seen[stamp]={'open':o,'close':cl,'valid':valid}
    return seen,{'path':str(path),'rows_scanned':total,'earliest_utc':utc([first])[0],
                 'latest_utc':utc([last])[0],'endpoint_labels_present':len(seen)},first,last

def midpoint_at(b,a,field):
    if b is None and a is None:return None,'BOTH_SIDES_ABSENT'
    if b is None:return None,'BID_ABSENT'
    if a is None:return None,'ASK_ABSENT'
    if not (b['valid'] and a['valid']):return None,'INVALID_SIDE_OHLC'
    bid=b[field];ask=a[field]
    if not (np.isfinite(bid) and np.isfinite(ask) and bid>0 and ask>0):return None,'INVALID_ENDPOINT_PRICE'
    if ask<bid:return None,'CROSSED_BID_ASK'
    mid=(ask+bid)*.5
    spread=10000*(ask-bid)/mid
    return (mid,spread),'OK'

def overnight_return(prev_close, next_open):
    if not (np.isfinite(prev_close) and np.isfinite(next_open) and prev_close>0 and next_open>0):
        return np.nan
    return float(np.log(next_open/prev_close))

def assemble_etf(name, p, edge, start, end):
    out=p.drop(columns=['prior_close_label_ns','next_open_label_ns','prior_close_ns','next_open_ns']).copy()
    out.insert(0,'source',name)
    out['source_epoch']='pitrading' if name.endswith('_LEGACY') else 'iex'
    out['legacy_timing_uncertain']=int(name.endswith('_LEGACY'))
    close=[];opening=[];status=[];r=[]
    for pr,nx in zip(p.prior_close_label_ns,p.next_open_label_ns):
        if pr<start or nx>end:
            pc=op=np.nan;reason='OUTSIDE_SOURCE_SPAN'
        else:
            pbar=edge.get(int(pr));nbar=edge.get(int(nx))
            pc=float(pbar[1]) if pbar else np.nan
            op=float(nbar[0]) if nbar else np.nan
            reason='OK' if pbar and nbar else ('BOTH_ENDPOINTS_MISSING' if not pbar and not nbar
                       else ('PRIOR_CLOSING_MINUTE_ABSENT' if not pbar else 'NEXT_OPENING_MINUTE_ABSENT'))
        close.append(pc);opening.append(op);status.append(reason)
        r.append(overnight_return(pc,op) if reason=='OK' else np.nan)
    out['prior_last_bar_close']=close;out['next_first_bar_open']=opening
    out['etf_overnight_log_return']=r
    out['etf_overnight_return_bp']=np.asarray(r)*10000.
    out['etf_status']=status
    out['etf_return_basis']='PRICE_ONLY_UNADJUSTED_FOR_DIVIDENDS'
    return out

def assemble_quote(name,p,bid,ask,low,high):
    out=p[['previous_session','session','prior_close_utc','next_open_utc','elapsed_minutes','break_kind','prior_early_close','conservative_available_utc']].copy()
    out.insert(0,'instrument',name)
    close=[];opening=[];spread_close=[];spread_open=[];status=[];baseline=[];strict=[]
    for prev,nxt in zip(p.prior_close_label_ns,p.next_open_label_ns):
        if int(prev)<low or int(nxt)>high:
            a0=a1=np.nan;s0=s1=np.nan;reason='OUTSIDE_SOURCE_SPAN'
        else:
            prior,reason_prior=midpoint_at(bid.get(int(prev)),ask.get(int(prev)),'close')
            nxtmid,reason_next=midpoint_at(bid.get(int(nxt)),ask.get(int(nxt)),'open')
            a0,s0=prior if prior is not None else (np.nan,np.nan)
            a1,s1=nxtmid if nxtmid is not None else (np.nan,np.nan)
            reason='OK' if reason_prior=='OK' and reason_next=='OK' else f'PRIOR:{reason_prior}|NEXT:{reason_next}'
        ret=overnight_return(a0,a1) if reason=='OK' else np.nan
        ret_strict=ret if np.isfinite(ret) and s0<=50 and s1<=50 else np.nan
        close.append(a0);opening.append(a1);spread_close.append(s0);spread_open.append(s1)
        status.append(reason);baseline.append(ret);strict.append(ret_strict)
    out['quote_mid_close_at_prior_close']=close
    out['quote_mid_open_at_next_open']=opening
    out['close_endpoint_spread_bp']=spread_close
    out['opening_endpoint_spread_bp']=spread_open
    out['quote_overnight_log_return']=baseline
    out['quote_overnight_bp']=np.asarray(baseline)*10000
    out['quote_overnight_log_return_spread50_sensitivity']=strict
    out['quote_overnight_bp_spread50_sensitivity']=np.asarray(strict)*10000
    out['quote_status']=status
    out['quote_tick_freshness_verified']=0
    out['quote_synthetic_bars_ruled_out']=0
    return out

def test():
    # Illustrative ordinary, shortened and weekend session pairs; same elapsed UTC clocks.
    sch=pd.DataFrame({'session':['2026-07-01','2026-07-02','2026-07-06'],
        'open_ns':ns(pd.Series(['2026-07-01T13:30:00Z','2026-07-02T13:30:00Z','2026-07-06T13:30:00Z'])),
        'close_ns':ns(pd.Series(['2026-07-01T20:00:00Z','2026-07-02T17:00:00Z','2026-07-06T20:00:00Z']))})
    sch['last_label_ns']=sch.close_ns-MIN
    p=pairs(sch)
    assert p.iloc[0].prior_early_close==0 and p.iloc[1].prior_early_close==1
    assert p.iloc[1].break_kind=='HOLIDAY_OR_EXTENDED_BREAK'
    assert p.iloc[0].elapsed_minutes==1050  # Wed 16:00 -> Thu 09:30 local
    q={int(p.prior_close_label_ns.iloc[0]):(99.,100.),int(p.next_open_label_ns.iloc[0]):(102.,103.),
       int(p.prior_close_label_ns.iloc[1]):(103.,104.)}
    z=assemble_etf('SPY_RAW',p,q,int(sch.open_ns.min()),int(sch.close_ns.max()))
    assert z.etf_status.iloc[0]=='OK'
    assert np.isclose(z.etf_overnight_log_return.iloc[0],np.log(102./100.))
    assert z.etf_status.iloc[1]=='NEXT_OPENING_MINUTE_ABSENT'
    assert np.isnan(z.etf_overnight_log_return.iloc[1])
    assert z.conservative_available_utc.iloc[0]=='2026-07-02T13:31:00Z'
    close_stamp=int(p.prior_close_label_ns.iloc[0]);open_stamp=int(p.next_open_label_ns.iloc[0])
    b={close_stamp:{'open':99.5,'close':100.,'valid':True},open_stamp:{'open':101.,'close':101.5,'valid':True}}
    a={close_stamp:{'open':100.5,'close':101.,'valid':True},open_stamp:{'open':102.,'close':102.5,'valid':True}}
    qq=assemble_quote('GOLD',p,b,a,int(sch.open_ns.min()),int(sch.close_ns.max()))
    assert np.isclose(qq.quote_overnight_log_return.iloc[0],np.log(101.5/100.5))
    assert np.isnan(qq.quote_overnight_log_return.iloc[1])
    crossed={'open':99.,'close':99.,'valid':True}
    assert midpoint_at(b[close_stamp],crossed,'close')[1]=='CROSSED_BID_ASK'
    # 2026 DST: NY opening UTC moves 14:30 -> 13:30 by March 9.
    assert pd.Timestamp('2026-03-06 09:30',tz='America/New_York').tz_convert('UTC').hour==14
    assert pd.Timestamp('2026-03-09 09:30',tz='America/New_York').tz_convert('UTC').hour==13
    # Returns must not accidentally change if unrelated *future* source value changes.
    z2=assemble_etf('SPY_RAW',p,{**q,int(p.prior_close_label_ns.iloc[1]):(103.,100000.)},int(sch.open_ns.min()),int(sch.close_ns.max()))
    assert z2.etf_overnight_log_return.iloc[0]==z.etf_overnight_log_return.iloc[0]
    print('SELF-TEST PASS: early close, weekend/holiday, exact endpoints, missing opens, quote pairing, crossed quotes, DST, availability, no future leakage',flush=True)

def run():
    test()
    OUT.mkdir(parents=True,exist_ok=True)
    sch=schedule();p=pairs(sch)
    print(f'XNYS: {len(sch):,} sessions; {len(p):,} consecutive overnight intervals',flush=True)
    metadata={'section':'3.7 Overnight/holidays/early closes','policy':{
      'ETF':'exact prior scheduled last-minute CLOSE to exact next scheduled first-minute OPEN',
      'GOLD_DOLLAR':'exact quote BID/ASK CLOSE midpoint to next quote BID/ASK OPEN midpoint',
      'labeling':'all quote/ETF labels are UTC normalized; historical PiTrading candle boundary UNVERIFIED',
      'opening_time_warning':'minute-bar OPEN is first trade/quote in opening minute, NOT guaranteed auction price or exact 9:30 tick',
      'earliest_safe_availability':'next open + 1 minute (conservative)',
      'dividend':'NOT ADJUSTED: price returns ONLY; Section 3.8 required',
      'raw_vs_legacy':'kept separate; cross-epoch overnight skipped',
      'missing_endpoint':'NO SUBSTITUTE, NO FILL',
      'quote_strict':'spread<=50bp both endpoints; overnight-only variant, NOT section 3.5 intraday full strict freshness screen',
      'quote_freshness':'UNVERIFIED; synthetic flat bars not individually identifiable',
      'overnight_interval':'one irregular elapsed interval, NEVER described as a 1m return'},
      'sessions':len(sch),'candidate_intervals':len(p),
      'quote_source_detail':{},'etf_source_detail':{},'quotes':{},'etfs':{}}
    quote_output={}
    all_targets=np.unique(np.r_[p.prior_close_label_ns.to_numpy(np.int64),p.next_open_label_ns.to_numpy(np.int64)])
    for name,files in Q_FILES.items():
        print(f'Loading quote endpoints for {name} (2 sides, streamed)...',flush=True)
        bid,bs,bsfirst,bslast=quote_side_edges(files['bid'],all_targets)
        ask,ass,asfirst,aslast=quote_side_edges(files['ask'],all_targets)
        lower=max(bsfirst,asfirst);upper=min(bslast,aslast)
        frame=assemble_quote(name,p,bid,ask,lower,upper)
        quote_output[name]=frame
        frame.to_csv(OUT/f'overnight_quote_{name}.csv.gz',index=False,compression='gzip',na_rep='')
        statuses=frame.quote_status.value_counts().to_dict()
        metadata['quote_source_detail'][name]={'bid':bs,'ask':ass}
        metadata['quotes'][name]={'candidate_intervals':len(frame),'valid_baseline':int(frame.quote_overnight_log_return.notna().sum()),
                                   'valid_spread50_sensitivity':int(frame.quote_overnight_log_return_spread50_sensitivity.notna().sum()),
                                   'status_counts':{str(k):int(v) for k,v in statuses.items()}}
        print(f'  {name}: {metadata["quotes"][name]["valid_baseline"]:,} valid overnight proxy returns',flush=True)
        del bid,ask
    for name in ETF_NAMES:
        print(f'Loading ETF endpoint candles: {name}...',flush=True)
        edges,es,earliest,latest=fetch_etf_edges(name,sch)
        frame=assemble_etf(name,p,edges,earliest,latest)
        # Join quote returns ONLY by exact previous/current exchange session identity.
        # Nonoverlap & missing cases remain as explicit NaNs and status flags.
        for qname,qf in quote_output.items():
            suffix=f'_{qname.lower()}'
            assert frame.session.equals(qf.session) and frame.previous_session.equals(qf.previous_session)
            frame[f'quote_overnight_bp{suffix}']=qf.quote_overnight_bp.to_numpy()
            frame[f'quote_overnight_bp_spread50{suffix}']=qf.quote_overnight_bp_spread50_sensitivity.to_numpy()
            frame[f'quote_status{suffix}']=qf.quote_status.to_numpy()
        frame.to_csv(OUT/f'overnight_etf_{name}.csv.gz',index=False,compression='gzip',na_rep='')
        within=frame.etf_status!='OUTSIDE_SOURCE_SPAN'
        both=frame.etf_status.eq('OK')
        metadata['etf_source_detail'][name]=es
        metadata['etfs'][name]={
           'candidate_intervals_within_source_span':int(within.sum()),
           'valid_overnight_etf_price_returns':int(both.sum()),
           'status_counts':{str(k):int(v) for k,v in frame.loc[within,'etf_status'].value_counts().items()},
           'paired_with_gold_valid':int((both & frame['quote_overnight_bp_gold'].notna()).sum()),
           'paired_with_dollar_valid':int((both & frame['quote_overnight_bp_dollar'].notna()).sum()),
           'early_close_valid':int((both & frame.prior_early_close.astype(bool)).sum()),
        }
        print(f'  {name}: {int(both.sum()):,} valid exact overnight intervals / {int(within.sum()):,} in span',flush=True)
        del edges,frame
    # Important cross-vendor boundary (2022-03-04 -> 2022-03-07) is NOT a return.
    transition=p[(p.previous_session=='2022-03-04')&(p.session=='2022-03-07')]
    assert len(transition)==1,'Expected 2022 boundary pair missing'
    metadata['2022_cross_epoch_boundary']={'interval':transition[['previous_session','session']].to_dict('records')[0],
        'etf_cross_vendor_overnight_return':'NOT CONSTRUCTED (requires harmonization Section 3.8/3.10)'}
    (OUT/'summary.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    lines=['# Section 3.7 — Overnight, holidays, early closes','',
      'One observation per **adjacent NYSE session close → next opening minute**; no minute interpolation, no invented ETF overnight candles.','',
      '## Exact ETF overnight price-return eligibility','',
      '| Dataset | Session pairs in input span | Valid endpoints | Missing endpoint pairs | Paired with gold | Paired with dollar |',
      '|---|---:|---:|---:|---:|---:|']
    for name,x in metadata['etfs'].items():
        lines.append(f'| {name} | {x["candidate_intervals_within_source_span"]:,} | {x["valid_overnight_etf_price_returns"]:,} | {x["candidate_intervals_within_source_span"]-x["valid_overnight_etf_price_returns"]:,} | {x["paired_with_gold_valid"]:,} | {x["paired_with_dollar_valid"]:,} |')
    lines+=['','## Exact gold/dollar endpoint proxy coverage','',
      '| Instrument | Valid baseline | Valid spread<=50bp at both endpoints |',
      '|---|---:|---:|']
    for name,x in metadata['quotes'].items():
        lines.append(f'| {name} | {x["valid_baseline"]:,} | {x["valid_spread50_sensitivity"]:,} |')
    lines+=['','## Interpretation and restrictions','',
      '- **Definition:** ETF prior last-minute CLOSE (known by exchange close) → next first-minute OPEN. For quote instruments, corresponding BID/ASK CLOSE midpoint → OPEN midpoint at matching UTC candle labels.',
      '- An OPEN of the 09:30 candle is NOT guaranteed to be an exact 09:30 exchange auction or live quote. Conservative information availability is stamped at 09:31 (or +1m of session open).',
      '- Short sessions use scheduled early close; weekends/holidays are retained as one irregular interval with actual elapsed minutes. No synthetic minute bar or zero return is created.',
      '- Missing 15:59/early-last-minute bars or missing 09:30 bars make a return ineligible; no last-seen substitution.',
      '- Gold and dollar are quote-based proxies with potentially asynchronous underlying side updates. Paired labels do not establish tick simultaneity or continuously reliable weekend quote paths.',
      '- Strict overnight quote **spread-only** sensitivity is NOT the 3.5 strict intraday filter (opening flat age is not yet known at 09:30).',
      '- All ETF returns here are unadjusted **price returns**. Dividend/ex-date effects must be addressed in 3.8 before causal event interpretation.',
      '- Historical ETF minute-start/end convention is still UNVERIFIED. All legacy overnight boundaries are conditional; investigate alternate alignment later.',
      '- The 2022-03-04 → 2022-03-07 ETF vendor-transition overnight return is deliberately NOT constructed.',
      '- These are endpoint-to-endpoint movements across irregular overnight intervals, not one-minute returns or guaranteed executable trading returns.',
      '', '## Artifacts (read-only sources unchanged)','',
      '- `overnight_etf_*.csv.gz`: one record per adjacent session pair, price returns, matched gold/dollar quote proxies, and explicit missing reason.',
      '- `overnight_quote_GOLD.csv.gz`, `overnight_quote_DOLLAR.csv.gz`: quote-only endpoint diagnostics and spread sensitivity.',
      '- `summary.json`: exact counts/qualifications. `REPORT.md`: concise findings.',
      '', '**Next:** Review eligibility and representative weekends/early closes; then freeze 3.7 and address dividends/source price basis in 3.8.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'SUCCESS. Results: {OUT}',flush=True)
    print('Upload REPORT.md and summary.json; keep compressed .csv.gz overnight panels locally.',flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--self-test',action='store_true');args=ap.parse_args()
    if args.self_test:test()
    else:run()

if __name__=='__main__':main()
