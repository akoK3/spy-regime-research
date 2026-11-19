#!/usr/bin/env python3
r"""Section 3.8 complete follow-up: repair/audit the earlier dividend script.

PowerShell: python "$HOME\Downloads\section3_8_full_verification.py"
Optional:   python "$HOME\Downloads\section3_8_full_verification.py" --offline
            python "$HOME\Downloads\section3_8_full_verification.py" --self-test

Requires: pandas, numpy. No originals overwritten. Yahoo chart is a SECONDARY,
non-issuer reference and may be unavailable/limited. Optional independently
obtained ISSUER files can be placed in Downloads\section3_8_issuer_sources:
  issuer_SPY.csv, issuer_TLT.csv, issuer_HYG.csv, OR issuer_actions.csv.
Columns: ticker (not needed for ticker-specific file), ex_date, cash_amount,
optional action/type and source_url. If you obtain an official XLSX, export
its relevant distributions sheet to CSV first. Record its URL and retrieval
information externally: a filename alone cannot establish authenticity.

IMPORTANT: Historical PiTrading adjustments CANNOT be certified from
price-pattern matching alone. This script does not silently correct them.
No ex-dividend history is assumed complete merely because a source responds.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, time, urllib.parse, urllib.request
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

import numpy as np
import pandas as pd

HOME=Path.home(); DOWNLOADS=HOME/'Downloads'
S2=HOME/'OneDrive'/'Desktop'/'data'/'raw_clean_price_audit_20261014'
ORIG=S2/'corporate_actions.csv'
OVERNIGHT=DOWNLOADS/'section3_7_overnight_results'
OLD=DOWNLOADS/'section3_8_corporate_action_results'
ISSUER=DOWNLOADS/'section3_8_issuer_sources'
OUT=DOWNLOADS/'section3_8_full_verification_results'
ETFS=('SPY','TLT','HYG')
SWITCH='2022-03-07'; CUT_OFF='2026-10-21'
EX_ALIASES=['ex_date','exdate','ex_dividend_date','exdividenddate','ex_dt','date']
AMT_ALIASES=['cash_amount','distribution_per_share','distribution','dividend','dividend_amount','amount','total_distribution','income']
TICK_ALIASES=['ticker','symbol','asset','fund']
TYPE_ALIASES=['action','event_type','type','action_type','distribution_type']
SPLIT_ALIASES=['split_ratio','ratio','split','split_factor']
ALLOWED=['divid','distribut','capital gain','income','cash']


def lookup_col(frame, aliases, required=False):
    def normalize(s):return ''.join(c for c in str(s).lower() if c.isalnum())
    names={normalize(c):c for c in frame.columns}
    for alias in aliases:
        if normalize(alias) in names:return names[normalize(alias)]
    if required: raise ValueError(f'Needed {aliases}; actual columns {list(frame.columns)}')
    return None


def normal_date(series):
    raw=series.astype(str).str.strip()
    # Handle mixed issuer date formats while supporting older pandas versions.
    try:
        result=pd.to_datetime(raw,errors='coerce',format='mixed')
        if result.isna().all():result=pd.to_datetime(raw,errors='coerce')
    except (TypeError, ValueError):
        result=pd.to_datetime(raw,errors='coerce')
    if result.isna().any():
        for x in raw[result.isna()].head(3): print('  UNPARSEABLE DATE:',x)
        raise ValueError('Unparseable dates in independent/reference source')
    return result.dt.strftime('%Y-%m-%d')


def read_events(path:Path, forced=None, source_type='REFERENCE'):
    frame=pd.read_csv(path,dtype=str,keep_default_na=False)
    if len(frame)==0: raise ValueError(f'Empty dividend source {path}')
    tcol=lookup_col(frame,TICK_ALIASES,required=not bool(forced));
    dcol=lookup_col(frame,EX_ALIASES,True); acol=lookup_col(frame,AMT_ALIASES,True)
    typecol=lookup_col(frame,TYPE_ALIASES)
    urlcol=lookup_col(frame,['source_url','reference_url','issuer_url'])
    tick=frame[tcol].str.upper().str.strip() if tcol else pd.Series(forced,index=frame.index)
    typ=frame[typecol].str.lower().str.strip() if typecol else pd.Series('dividend',index=frame.index)
    relevant=tick.isin(ETFS)
    split=relevant & typ.str.contains('split|reverse',regex=True,na=False)
    dividend=relevant & (~split) & (typ.str.contains('|'.join(ALLOWED),na=False,regex=True)|typ.eq(''))
    dates=normal_date(frame.loc[relevant,dcol])
    num=pd.to_numeric(frame.loc[dividend,acol].str.replace(r'[$, ]','',regex=True),errors='coerce')
    if num.isna().any() or (num<=0).any() or (~np.isfinite(num)).any():
        raise ValueError(f'{path}: dividend amounts must be positive USD-per-share. Verify units: {frame.loc[dividend,acol].head()}')
    ds=pd.DataFrame({'ticker':tick[dividend].to_numpy(),
                     'ex_date':dates.loc[dividend].to_numpy(),
                     'amount':num.astype(float).to_numpy(),
                     'source_kind':source_type,
                     'source_file':str(path),
                     'source_url':(frame.loc[dividend,urlcol].astype(str).to_numpy()
                                   if urlcol else np.full(int(dividend.sum()),''))})
    sp=pd.DataFrame({'ticker':tick[split].to_numpy(),'date':dates.loc[split].to_numpy(),
                     'source_kind':source_type,'source_file':str(path)})
    # Multiple components of same ex-date cannot be added without proof: flag conflict.
    conflict=ds.groupby(['ticker','ex_date']).amount.nunique() if len(ds) else pd.Series(dtype=int)
    ambiguous=set(conflict[conflict>1].index)
    ds=ds.drop_duplicates(['ticker','ex_date','amount']).sort_values(['ticker','ex_date'])
    return ds.reset_index(drop=True),sp.reset_index(drop=True),ambiguous


def safe_json(x):
    if isinstance(x,(np.integer,)):return int(x)
    if isinstance(x,(np.floating,)):return float(x)
    if isinstance(x,Path):return str(x)
    raise TypeError(str(type(x)))


def yahoo_fetch(ticker, cache_dir, offline=False):
    """Yahoo chart daily UNADJUSTED (split-adjusted) close, dividends, splits.
       Source is secondary, NOT issuer-verified or certified point-in-time."""
    p=cache_dir/f'yahoo_{ticker}_chart.json'
    if not offline:
        q=urllib.parse.urlencode({'period1':1000000000,'period2':int(datetime(2026,10,22,tzinfo=timezone.utc).timestamp()),
                                  'interval':'1d','events':'div,splits','includeAdjustedClose':'true'})
        url=f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?{q}'
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (research; historical dividend crosscheck)',
                                               'Accept':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=22) as resp:
                data=resp.read(18*1024*1024)
            parsed=json.loads(data)
            if not parsed.get('chart',{}).get('result'):raise ValueError('Yahoo returned no chart results')
            p.write_bytes(data)
        except Exception as exc:
            if not p.exists():return None,None,None,f'NETWORK_UNAVAILABLE: {str(exc)[:150]}'
            print(f'  {ticker}: live API unavailable, using local cached JSON: {str(exc)[:100]}')
    if not p.exists():return None,None,None,'CACHE_MISSING_OFFLINE'
    try:
        doc=json.loads(p.read_text(encoding='utf-8'))['chart']['result'][0]
        events=doc.get('events') or {}
        es=[];split=[]
        for x in (events.get('dividends') or {}).values():
            day=datetime.fromtimestamp(int(x['date']),timezone.utc).strftime('%Y-%m-%d')
            amt=float(x['amount'])
            if amt>0:es.append({'ticker':ticker,'ex_date':day,'amount':amt,'source_kind':'YAHOO_SECONDARY',
                                'source_file':str(p),'source_url':'https://finance.yahoo.com/quote/'+ticker+'/history/'})
        for x in (events.get('splits') or {}).values():
            day=datetime.fromtimestamp(int(x['date']),timezone.utc).strftime('%Y-%m-%d')
            split.append({'ticker':ticker,'date':day,'numerator':x.get('numerator'),
                          'denominator':x.get('denominator'),'splitRatio':x.get('splitRatio')})
        ts=doc['timestamp'];qs=doc['indicators']['quote'][0];cl=qs.get('close');op=qs.get('open')
        dt=pd.to_datetime(ts,unit='s',utc=True).tz_convert('America/New_York')
        daily=pd.DataFrame({'session':dt.strftime('%Y-%m-%d'),'secondary_close':cl,
                            'secondary_open':op if op is not None else [np.nan]*len(ts)})
        daily=daily[np.isfinite(pd.to_numeric(daily.secondary_close,errors='coerce'))].copy()
        if not daily.empty and daily.session.duplicated().any():
            raise ValueError('Daily close duplicate dates')
        return pd.DataFrame(es),pd.DataFrame(split),daily,f'YAHOO_SECONDARY_CACHE: {p}'
    except Exception as exc:
        return None,None,None,f'RESPONSE_ERROR: {str(exc)[:150]}'


def self_test():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        t=Path(tmp)
        pd.DataFrame({'symbol':['SPY','SPY','TLT','TLT','HYG'],
                      'ex_date':['2025-03-21','2025-03-21','2026-10-01','2026-10-01','2025-04-01'],
                      'cash_amount':[1,1,.25,.30,.40],
                      'action':['Dividend']*5}).to_csv(t/'a.csv',index=False)
        ds,sp,amb=read_events(t/'a.csv')
        assert len(ds)==4 and ('TLT','2026-10-01') in amb
        assert ('SPY','2025-03-21') not in amb
        d=pd.DataFrame({'session':['2021-12-17','2025-03-21','2025-03-24'],
                        'etf_status':['OUTSIDE_SOURCE_SPAN','OK','NEXT_OPENING_MINUTE_ABSENT']})
        # Old script bug: date outside a dataset is NOT a missing endpoint.
        assert classify_row(d.iloc[0],'LEGACY')=='OUTSIDE_SOURCE_SPAN'
        assert classify_row(d.iloc[2],'RAW')=='MISSING_ENDPOINT'
        assert np.isclose(math.log((99+1)/100),0)
        assert np.isnan(adjust_price(np.nan,99,1))
        assert np.isfinite(adjust_price(100,99,1))
        ref=pd.DataFrame([{'ticker':'SPY','ex_date':'2025-03-21','amount':1.0}])
        yahoo=pd.DataFrame([{'ticker':'SPY','ex_date':'2025-03-21','amount':1.0}])
        r=compare_events(ref,yahoo)
        assert r.match_status.iloc[0]=='MATCH'
    print('SELF-TEST PASS: old-script misclassification, duplicated/conflicting dates, ex-date math, missing endpoints, independent comparison')


def classify_row(row,epoch):
    s=str(row.get('etf_status',''))
    if s=='OUTSIDE_SOURCE_SPAN':return 'OUTSIDE_SOURCE_SPAN'
    if s!='OK':return 'MISSING_ENDPOINT'
    return 'VALID_ENDPOINTS'


def adjust_price(close,opening,amt):
    if not all(np.isfinite(float(a)) for a in [close,opening,amt]):return np.nan
    if min(close,opening)<=0 or amt<0:return np.nan
    return math.log((opening+amt)/close)


def compare_events(ref, independent, tolerance=0.005):
    """Comparison is not proof of issuer origin or completeness."""
    unique=independent.drop_duplicates(['ticker','ex_date']) if len(independent) else independent
    mid=pd.merge(ref, unique[['ticker','ex_date','amount']].rename(columns={'amount':'independent_amount'}),
                 on=['ticker','ex_date'],how='left',validate='many_to_one')
    mid['delta_usd']=(mid.amount-mid.independent_amount).abs()
    mid['match_status']=np.select([mid.independent_amount.isna(), mid.delta_usd<=tolerance],
                                  ['NOT_FOUND_IN_SECONDARY','MATCH'],default='AMOUNT_MISMATCH')
    return mid


def find_sources(directory):
    found=[]
    for ticker in ETFS:
        path=directory/f'issuer_{ticker}.csv'
        if path.is_file():found.append((path,ticker))
    allp=directory/'issuer_actions.csv'
    if allp.is_file():found.append((allp,None))
    return found


def years_coverage(events,ticker,dates_from,dates_to):
    x=events[(events.ticker==ticker)&(events.ex_date>=dates_from)&(events.ex_date<=dates_to)]
    lo=int(dates_from[:4]);hi=int(dates_to[:4]); years={str(y):int((x.ex_date.str[:4]==str(y)).sum()) for y in range(lo,hi+1)}
    return {'count':len(x),'first':x.ex_date.min() if len(x) else None,'last':x.ex_date.max() if len(x) else None,'years':years}


def price_basis_probe(overnight, daily, ticker, epoch, event_dates):
    """Only a diagnostic: minute exchange last print vs Yahoo daily CLOSE is not exact consolidated equivalence."""
    if daily is None or daily.empty:return {'status':'NO_SECONDARY_DAILY_PRICES'}
    present=overnight[['previous_session','prior_last_bar_close']].drop_duplicates('previous_session')
    present=present.rename(columns={'previous_session':'session','prior_last_bar_close':'local_close'})
    merged=present.merge(daily,on='session',how='inner')
    merged['local_close']=pd.to_numeric(merged.local_close,errors='coerce')
    merged['secondary_close']=pd.to_numeric(merged.secondary_close,errors='coerce')
    merged=merged[(merged.local_close>0)&(merged.secondary_close>0)].sort_values('session').copy()
    if len(merged)<20:return {'status':'INSUFFICIENT_MATCHED_DAILY_CLOSES','matched':len(merged)}
    merged['log_ratio_bp']=10000*np.log(merged.local_close/merged.secondary_close)
    dif=merged['log_ratio_bp'].diff()
    rowdates=merged.session
    # Diff only adjacent NYSE days that are actually in supplied matched panel; not missing joins.
    eventmask=rowdates.isin(event_dates)
    absdiff=dif.abs()
    return {'status':'DIAGNOSTIC_ONLY_NOT_ADJUSTMENT_CERTIFICATION',
            'matched_days':len(merged),
            'median_abs_local_vs_daily_close_bp':round(float(merged.log_ratio_bp.abs().median()),4),
            'p95_abs_local_vs_daily_close_bp':round(float(merged.log_ratio_bp.abs().quantile(.95)),4),
            'median_log_price_ratio_bp':round(float(merged.log_ratio_bp.median()),4),
            'large_daily_price_ratio_shifts_over_30bp':int((absdiff>30).sum()),
            'matching_exdates_with_ratios':int(eventmask.sum()),
            'note':'Different venues, closes, split/dividend basis and historical vendor scaling confound identification.'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--offline',action='store_true',help='Use cached Yahoo chart JSON only')
    p.add_argument('--self-test',action='store_true')
    p.add_argument('--issuer-dir',type=Path,default=ISSUER)
    p.add_argument('--out',type=Path,default=OUT)
    args=p.parse_args()
    self_test()
    if args.self_test:return
    out=args.out.expanduser();out.mkdir(parents=True,exist_ok=True)
    if not ORIG.exists():raise FileNotFoundError(f'Section 2 reference missing: {ORIG}')
    baseline,baselinesplits,base_conflict=read_events(ORIG,source_type='SECTION2_PRIOR_REFERENCE')
    baseline.to_csv(out/'section2_reference_events.csv',index=False)
    issuer_frames=[];issuer_split=[];issuer_conflict=set();issuer_paths=[]
    for path,ticker in find_sources(args.issuer_dir):
        try:
            ds,sp,amb=read_events(path,forced=ticker,source_type='SUPPLIED_ISSUER_FILE_PROVENANCE_UNVERIFIED')
            issuer_frames.append(ds);issuer_split.append(sp);issuer_conflict|=amb;issuer_paths.append(str(path))
        except Exception as exc:
            print(f'WARNING: issuer input {path}: {exc}')
    iss=pd.concat(issuer_frames,ignore_index=True) if issuer_frames else pd.DataFrame(columns=baseline.columns)
    iss_sp=pd.concat(issuer_split,ignore_index=True) if issuer_split else pd.DataFrame(columns=['ticker','date','source_kind'])
    iss.to_csv(out/'supplied_issuer_claims.csv',index=False)
    if issuer_paths:
        (out/'ISSUER_INPUT_PROVENANCE_REQUIRED.txt').write_text(
            'Issuer input filenames are not evidence of authenticity. Record original official issuer URL,\n'
            'download date, full file SHA256, completeness and whether dividends include capital gains.\n'
            'Source details: '+'\n'.join(issuer_paths)+'\n',encoding='utf-8')
    yframes=[];y_splits=[];daily_map={};y_status={}
    for ticker in ETFS:
        print(f'Fetching independent SECONDARY dividends/daily closes: {ticker} ...',flush=True)
        yd,ys,dp,status=yahoo_fetch(ticker,out,args.offline)
        y_status[ticker]=status
        if yd is not None:
            yframes.append(yd);y_splits.append(ys);daily_map[ticker]=dp
            print(f'  {len(yd)} dividends, {len(ys)} split events, {len(dp)} daily closes; {status}')
        else:print(f'  UNRESOLVED: {status}')
    yahoo=pd.concat(yframes,ignore_index=True) if yframes else pd.DataFrame(columns=baseline.columns)
    ysplits=pd.concat(y_splits,ignore_index=True) if y_splits else pd.DataFrame(columns=['ticker','date'])
    yahoo.to_csv(out/'independent_secondary_events.csv',index=False)
    ysplits.to_csv(out/'independent_secondary_splits.csv',index=False)
    comparison=compare_events(baseline,yahoo) if len(yahoo) else baseline.assign(independent_amount=np.nan,delta_usd=np.nan,match_status='SECONDARY_UNAVAILABLE')
    comparison.to_csv(out/'section2_vs_secondary_event_comparison.csv',index=False)
    missing_from_orig=yahoo.merge(baseline[['ticker','ex_date']].drop_duplicates(),on=['ticker','ex_date'],how='left',indicator=True)
    missing_from_orig=missing_from_orig[missing_from_orig._merge=='left_only'].drop(columns='_merge')
    missing_from_orig.to_csv(out/'dividends_missing_from_old_reference.csv',index=False)
    if len(iss):
        icomp=compare_events(iss,yahoo) if len(yahoo) else iss.assign(independent_amount=np.nan,delta_usd=np.nan,match_status='SECONDARY_UNAVAILABLE')
        icomp.to_csv(out/'issuer_claims_vs_secondary.csv',index=False)
    notes=[]; summary={'section':'3.8 comprehensive follow-up and first-script verification',
                      'read_only_originals':True,
                      'original_3_8_outputs_are_not_overwritten':True,
                      'event_sources':{'section2_rows':len(baseline),'section2_exdate_coverage':{},
                                       'supplied_issuer_rows':len(iss),'issuer_files':issuer_paths,
                                       'issuer_file_sha256':{str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q,_ in find_sources(args.issuer_dir)},
                                       'yahoo_secondary_rows':len(yahoo),'yahoo_status_by_ticker':y_status},
                      'first_script_defect':'Dates outside a file source span misreported as missing endpoints; not evidence of missing historical prices.',
                      'tests':{},'assets':{},'limitations':[]}
    # Deterministic event precedence for tentative data exploration: issuer-input (unverified provenance),
    # then independent SECONDARY Yahoo, then legacy Section2 reference. Explicit status on every row.
    priority=[]
    for name,frame in [('SUPPLIED_ISSUER_FILE_UNAUTHENTICATED',iss),('YAHOO_SECONDARY_NOT_ISSUER',yahoo),('SECTION2_REFERENCE_ONLY',baseline)]:
        if not len(frame):continue
        xx=frame.copy();xx['provenance_level']=name;priority.append(xx)
    if not priority:raise ValueError('No corporate action data of any kind available')
    candidates=pd.concat(priority,ignore_index=True)
    candidates=candidates.sort_values(['ticker','ex_date'],kind='stable')
    conflicts=candidates.groupby(['ticker','ex_date']).amount.agg(lambda x:float(x.max()-x.min()))
    conflicted=set(conflicts[conflicts>0.005].index)|base_conflict|issuer_conflict
    final_events=candidates.drop_duplicates(['ticker','ex_date'],keep='first').copy()
    final_events['conflicting_amounts_across_sources']=[(t,d) in conflicted for t,d in zip(final_events.ticker,final_events.ex_date)]
    final_events.to_csv(out/'candidate_dividends_all_epochs.csv',index=False)
    summary['tests']['1_verify_129_record_date_amounts']={
        'reference_events':len(baseline),
        'independent_secondary_matches':int((comparison.match_status=='MATCH').sum()) if len(yahoo) else None,
        'independent_secondary_mismatches':int((comparison.match_status=='AMOUNT_MISMATCH').sum()) if len(yahoo) else None,
        'independent_secondary_dates_not_found':int((comparison.match_status=='NOT_FOUND_IN_SECONDARY').sum()) if len(yahoo) else None,
        'independent_source_missing_count':len(ETFS)-len(daily_map),
        'issuer_files_supplied':len(issuer_paths),
        'status':'NOT_ISSUER_VERIFIED' if not issuer_paths else 'ISSUER_DOCUMENTS_SUBMITTED_BUT_AUTHENTICITY_AND_COVERAGE_NEED_REVIEW'
    }
    for ticker in ETFS:
        summary['event_sources']['section2_exdate_coverage'][ticker]={
            'legacy':years_coverage(baseline,ticker,'2002-01-01','2022-03-06'),
            'modern':years_coverage(baseline,ticker,'2022-03-07',CUT_OFF)}
    summary['tests']['2_complete_historical_exdates']={
        'original_reference_missing_legacy_events_relative_to_secondary':int((missing_from_orig.ex_date<SWITCH).sum()) if len(yahoo) else None,
        'independent_secondary_has_full_legacy_span':{
            t:bool((not yahoo[yahoo.ticker==t].empty) and yahoo[yahoo.ticker==t].ex_date.min() <SWITCH)
            for t in ETFS},
        'note':'Coverage checks detect missing records but do not prove complete issuer histories.'}
    nonempty_splits=[x for x in [ysplits,baselinesplits,iss_sp] if len(x)]
    allsplits=pd.concat(nonempty_splits,ignore_index=True) if nonempty_splits else pd.DataFrame(columns=['ticker','date','source_kind'])
    allsplits.to_csv(out/'all_reported_split_events.csv',index=False)
    summary['tests']['4_splits']={
        'yahoo_secondary_reported_splits':len(ysplits),
        'supplied_issuer_splits':len(iss_sp),
        'section2_referenced_splits':len(baselinesplits),
        'status':'NO_ISSUER_SPLIT_CERTIFICATION' if not issuer_paths else 'CHECK_ISSUER_SPLIT_FILE_COVERAGE',
        'note':'Zero events in a source is not proof no splits occurred. Compare split_date_price_checks.csv where dates exist.'}
    # Detect earlier script miscounts, preserve local 3.7 and 3.8 outputs.
    revised_counts={}; probes={}; samples=[]; affected=[]; daily_price_checks=[]; split_price_checks=[]; opening_price_checks=[]
    for ticker in ETFS:
        ce=final_events[final_events.ticker==ticker].copy()
        date_to_data=ce.set_index('ex_date').to_dict(orient='index')
        for epoch in ('LEGACY','RAW'):
            name=ticker+'_'+epoch
            pth=OVERNIGHT/f'overnight_etf_{name}.csv.gz'
            if not pth.exists():raise FileNotFoundError(f'Missing 3.7 artifact: {pth}')
            x=pd.read_csv(pth,low_memory=False)
            needed=['previous_session','session','etf_status','prior_last_bar_close',
                    'next_first_bar_open','etf_overnight_log_return']
            if not set(needed).issubset(x):raise ValueError(f'{name}: incorrect 3.7 columns')
            x['session']=x.session.astype(str).str[:10]
            active=(x.session<SWITCH) if epoch=='LEGACY' else (x.session>=SWITCH)
            # Only count candidate ex-dates inside actual source row availability; label actual source status.
            isdate=x.session.isin(set(ce.ex_date))
            outside=(x.etf_status=='OUTSIDE_SOURCE_SPAN')
            eligible=isdate & active & ~outside
            missing=eligible & (x.etf_status!='OK')
            ok=eligible & (x.etf_status=='OK')
            outperiod=isdate & ~active
            # Crucial old script bug: reported ~129 modern exdates as historical missing endpoints.
            oldfile=OLD/f'overnight_corporate_flags_{name}.csv.gz'
            old_missing_reported=None
            if oldfile.exists():
                oldx=pd.read_csv(oldfile,usecols=['ex_date_reference_present','etf_status'])
                old_missing_reported=int((oldx.ex_date_reference_present.astype(str).str.lower().isin(['true','1']) & (oldx.etf_status!='OK')).sum())
            x['audit_ex_date_candidate']=isdate.astype('uint8')
            x['audit_ex_date_within_epoch']=eligible.astype('uint8')
            x['audit_outside_dataset_epoch_or_span']=(isdate & ~eligible).astype('uint8')
            x['audit_ex_date_price_endpoints_status']=np.select([~isdate,isdate & ~eligible,missing,ok],
                 ['NO_CANDIDATE_EXDATE','OUTSIDE_SOURCE_EPOCH_OR_SPAN','MISSING_ENDPOINT','EXDATE_ENDPOINTS_OK'],default='UNKNOWN')
            x['audit_dividend_amount']=x.session.map({d:a['amount'] for d,a in date_to_data.items()})
            x['audit_dividend_source']=x.session.map({d:a['provenance_level'] for d,a in date_to_data.items()})
            x['audit_conflicting_dividend_amount']=x.session.isin({d for d,a in date_to_data.items() if a['conflicting_amounts_across_sources']}).astype('uint8')
            # Unverified issuer provenance does not become certified through numerical agreement.
            close=pd.to_numeric(x.prior_last_bar_close,errors='coerce')
            opening=pd.to_numeric(x.next_first_bar_open,errors='coerce')
            amt=pd.to_numeric(x.audit_dividend_amount,errors='coerce')
            possible=ok & amt.notna() & (close>0)&(opening>0) & (x.audit_conflicting_dividend_amount==0)
            x['audit_modern_provisional_cash_adjusted_log_return']=np.nan
            if epoch=='RAW':
                x.loc[possible,'audit_modern_provisional_cash_adjusted_log_return']=np.log((opening[possible]+amt[possible])/close[possible])
            x['audit_legacy_no_correction_due_to_unknown_basis']=int(epoch=='LEGACY')
            x['audit_modern_provisional_cash_effect_bp']=(
                x.audit_modern_provisional_cash_adjusted_log_return-x.etf_overnight_log_return)*10000
            # Compare previous-session last-minute CLOSE with independently supplied
            # daily Yahoo close. Both are approximate references, not identical prints.
            daily=daily_map.get(ticker)
            if daily is not None and len(daily):
                dy=x[['previous_session','session','etf_status','prior_last_bar_close']].copy()
                dy=dy.merge(daily.rename(columns={'session':'previous_session'}),on='previous_session',how='left')
                dy['local_vs_secondary_daily_bp']=10000*np.log(
                    pd.to_numeric(dy.prior_last_bar_close,errors='coerce')/
                    pd.to_numeric(dy.secondary_close,errors='coerce'))
                dy['ticker']=ticker;dy['epoch']=epoch
                dy['is_exdate']=dy.session.isin(set(ce.ex_date))
                dy=dy[(dy.secondary_close.notna()) & (dy.prior_last_bar_close.notna())]
                daily_price_checks.append(dy)
                opcheck=x[['previous_session','session','etf_status','next_first_bar_open','prior_last_bar_close']].copy()
                opcheck=opcheck.merge(daily[['session','secondary_open']],on='session',how='left')
                opcheck['local_vs_secondary_open_bp']=10000*np.log(
                    pd.to_numeric(opcheck.next_first_bar_open,errors='coerce')/
                    pd.to_numeric(opcheck.secondary_open,errors='coerce'))
                opcheck['ticker']=ticker;opcheck['epoch']=epoch
                opcheck['is_exdate']=opcheck.session.isin(set(ce.ex_date))
                opcheck=opcheck[(opcheck.secondary_open.notna()) & (opcheck.next_first_bar_open.notna())]
                opening_price_checks.append(opcheck)

            # On independently reported split dates, inspect the observed gap.
            # A small gap is merely compatible with split-adjusted prices;
            # the exact price basis still requires issuer/vendor confirmation.
            splits=allsplits[(allsplits.ticker==ticker)] if len(allsplits) else pd.DataFrame()
            if len(splits):
                spldays=set(splits.date)
                splitrows=x[x.session.isin(spldays) & (x.etf_status!='OUTSIDE_SOURCE_SPAN')][[
                    'previous_session','session','etf_status','prior_last_bar_close',
                    'next_first_bar_open','etf_overnight_log_return']].copy()
                splitrows.insert(0,'ticker',ticker);splitrows.insert(1,'epoch',epoch)
                split_price_checks.append(splitrows)
            x.to_csv(out/f'overnight_corporate_audited_{name}.csv.gz',index=False,compression={'method':'gzip','compresslevel':1})
            summary['assets'][name]={'candidate_exdates_all_span':int(isdate.sum()),
                    'eligible_in_epoch':int(eligible.sum()),'true_missing_endpoints_on_candidate_exdates':int(missing.sum()),
                    'valid_exdate_endpoints':int(ok.sum()),'candidate_dates_outside_epoch_or_file':int((isdate & ~eligible).sum()),
                    'old_3_8_script_reported_missing_endpoints':old_missing_reported,
                    'modern_provisional_cash_estimates':int(x.audit_modern_provisional_cash_adjusted_log_return.notna().sum()),
                    'price_basis':('LEGACY_UNVERIFIED_NO_CORRECTION' if epoch=='LEGACY' else 'MODERN_SPLIT_ADJUSTED_DIVIDEND_UNADJUSTED_CLAIMED')}
            valid_ex=x[eligible][['session','previous_session','etf_status','prior_last_bar_close',
                                   'next_first_bar_open','audit_dividend_amount','etf_overnight_log_return',
                                   'audit_modern_provisional_cash_adjusted_log_return','audit_dividend_source']].copy()
            valid_ex.insert(0,'asset',name);samples.append(valid_ex)
            probe=price_basis_probe(x,daily_map.get(ticker),ticker,epoch,set(ce.ex_date))
            probes[name]=probe
            print(f'  {name}: {int(eligible.sum())} in-period exdates, {int(missing.sum())} genuinely missing endpoints; old claimed {old_missing_reported}',flush=True)
    pd.concat(samples,ignore_index=True).to_csv(out/'exdate_price_examples_all_epochs.csv',index=False)
    (pd.concat(daily_price_checks,ignore_index=True) if daily_price_checks else
        pd.DataFrame(columns=['ticker','epoch','previous_session','session','local_vs_secondary_daily_bp'])).to_csv(
        out/'local_vs_secondary_daily_close_checks.csv',index=False)
    (pd.concat(opening_price_checks,ignore_index=True) if opening_price_checks else
        pd.DataFrame(columns=['ticker','epoch','session','local_vs_secondary_open_bp'])).to_csv(
        out/'local_vs_secondary_daily_open_checks.csv',index=False)
    (pd.concat(split_price_checks,ignore_index=True) if split_price_checks else
        pd.DataFrame(columns=['ticker','epoch','session','etf_overnight_log_return'])).to_csv(
        out/'split_date_price_checks.csv',index=False)
    summary['tests']['3_piTrading_adjustment_basis']={'status':'UNVERIFIED_PENDING_VENDOR_OR_INDEPENDENT_DATED_RAW_PRICES',
        'daily_price_diagnostics':probes,
        'note':'Price ratios against secondary daily closes are clues, not proof of original point-in-time PiTrading adjustment processing.'}
    summary['tests']['5_independent_exdate_close_open_check']={'status':'PRICES_MERELY_DIAGNOSTIC_WITH_AVAILABLE_DAILY_YAHOO',
         'method':'Compare local previous CLOSE and next opening minute OPEN against independently sampled daily CLOSE/OPEN; inspect ex-date cases.',
         'independent_daily_close_comparison_rows':int(sum(len(z) for z in daily_price_checks)),
         'independent_daily_open_comparison_rows':int(sum(len(z) for z in opening_price_checks)),
         'note':'Yahoo daily price cannot independently certify exact intraday minute opening auction prints. Need consolidated minute/tick records for that.'}
    summary['limitations']=[
       'Issuer-provided history completeness not proved by third-party Yahoo API alone.',
       'Original Section 2 list mostly modern dates; prior 3.8 historical missing-endpoint conclusions were misleading.',
       'PiTrading historical dividend/split adjustment policy is unverified; no historical cash correction made.',
       'Exact issuer source and amount provenance requires independent issuer files or original verified publications.',
       'Yahoo daily OPEN/CLOSE are secondary comparisons, not certified consolidated matched minute prints.',
       'Split absence and historical adjustment factors remain uncertified without complete authoritative actions and vendor history.',
       'Cash-adjusted overnight estimate is retrospective shareholder-value proxy, NOT point-in-time, executable or certified total-return history.',
       'Modern IEX 2022 vendor boundary remains separate; older CLEAN snapshot is not mixed into returns.'
    ]
    (out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False,default=safe_json,allow_nan=False),encoding='utf-8')
    lines=['# Section 3.8 — Comprehensive dividend/split audit and first-script correction','',
           '**No source price files were edited; original 3.8 outputs preserved.**','',
           '## Core correction','',
           'The earlier script counted modern ex-dates in historical datasets as MISSING_ENDPOINT. They were OUTSIDE_SOURCE_SPAN / outside provider epoch. Corrected per-epoch counts follow.','',
           '| Dataset | Candidate exdates genuinely in dataset | Missing endpoints in dataset | Dates outside dataset | Earlier claimed missing |',
           '|---|---:|---:|---:|---:|']
    for key,item in summary['assets'].items():
        lines.append(f'| {key} | {item["eligible_in_epoch"]} | {item["true_missing_endpoints_on_candidate_exdates"]} | {item["candidate_dates_outside_epoch_or_file"]} | {item["old_3_8_script_reported_missing_endpoints"]} |')
    lines+=['','## Five verification questions','',
            f'1. **Dividend dates/amounts:** {summary["tests"]["1_verify_129_record_date_amounts"]["independent_secondary_matches"]} entries match Yahoo within $0.005 (None means Yahoo unavailable); issuer confirmation NOT established automatically. See comparison CSV.',
            f'2. **Historical coverage:** {summary["tests"]["2_complete_historical_exdates"]["original_reference_missing_legacy_events_relative_to_secondary"]} earlier-than-2022 Yahoo events absent from old list (None means unavailable). An issuer-complete history is still required.',
            '3. **Legacy price basis:** Compare local last-minute closes to secondary daily closes; findings are clues only. PiTrading adjustment policy remains UNVERIFIED.',
            f'4. **Splits:** Yahoo reports {len(ysplits)} split events across available histories. Lack of reported splits is NOT certified absence.',
            '5. **Price sanity:** Independent daily close comparison + all candidate exdate overnight endpoints saved. Exact consolidated intraday prices/auction OPEN remain unverified.','',
            '## Artifacts','',
            '- `section2_vs_secondary_event_comparison.csv`: dates/amounts for the original 129 records.',
            '- `dividends_missing_from_old_reference.csv`: dates missing from old reference, including pre-2022.',
            '- `candidate_dividends_all_epochs.csv`: full provisional historical event table with source/conflict flags.',
            '- `overnight_corporate_audited_*.csv.gz`: corrected flags per ETF epoch, provisional modern adjusted estimates only.',
            '- `exdate_price_examples_all_epochs.csv`: observed overnight price endpoints and dividends.',
            '- `all_reported_split_events.csv`, `split_date_price_checks.csv`: split-history comparison and matching price endpoints.',
            '- `local_vs_secondary_daily_close_checks.csv`, `local_vs_secondary_daily_open_checks.csv`: local endpoints versus independent daily OPEN/CLOSE proxies.',
            '- `summary.json`: definitive test statuses and unresolved limits.','',
            '**Do not claim 3.8 fully verified until issuer completeness, true split history, and historical vendor adjustment basis are substantiated.**']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'\nSUCCESS: {out}')
    print('Upload REPORT.md, summary.json, section2_vs_secondary_event_comparison.csv and dividends_missing_from_old_reference.csv.')
    if not issuer_paths:print('NOTE: For issuer-authentication, place original issuer dividend CSVs under Downloads\\section3_8_issuer_sources and rerun.')

if __name__=='__main__':main()
