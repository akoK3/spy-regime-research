#!/usr/bin/env python3
r"""Section 3.8: final four verification checks (evidence-qualified).

Run: python "$HOME\Downloads\section3_8_final_four_checks.py"
Offline (cached Yahoo + optional issuer files): python "$HOME\Downloads\section3_8_final_four_checks.py" --offline

Inputs: earlier 3.7 and 3.8 full-verification output. Python pandas and numpy.
Optional: issuer-verified CSV exports in Downloads/section3_8_issuer_sources:
 issuer_SPY.csv, issuer_TLT.csv, issuer_HYG.csv, issuer_actions.csv
with ticker(optional in ticker-specific), ex_date, cash_amount. Preserve original
issuer download/URL in source_provenance.txt. A CSV's filename does not establish
its authenticity. Source pages below are separate from supplied files.

Never rewrites source or existing report. Never makes a historic cash correction.
Official web results may be partial/blocked; explicitly labelled when so.
"""
from __future__ import annotations
import argparse, collections, datetime as dt, hashlib, html, io, json, math, re, sys
from pathlib import Path
import urllib.request
import urllib.error
import pandas as pd
import numpy as np

HOME=Path.home(); DL=HOME/'Downloads'
OLD=DL/'section3_8_full_verification_results'
OVERNIGHT=DL/'section3_7_overnight_results'
ISSUER=DL/'section3_8_issuer_sources'
OUT=DL/'section3_8_final_checks_results'
TICKERS=('SPY','TLT','HYG'); SWITCH='2022-03-07'
ISSUER_URLS={
 'SPY':'https://www.ssga.com/us/en/individual/resources/documents/etf-dividend-distributions',
 'TLT':'https://www.ishares.com/us/products/239454/ishares-20-year-treasury-bond-etf',
 'HYG':'https://www.ishares.com/us/products/239565/ishares-iboxx-high-yield-corporate-bond-etf',
}
PITRADING_URL='https://pitrading.com/historical-stock-data.html'
UA='Mozilla/5.0 (compatible; AcademicResearchAudit/1.0; ETF corporate actions)'

def get(url,timeout=18,max_bytes=10_000_000):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        body=r.read(max_bytes+1)
        if len(body)>max_bytes:raise ValueError('download larger than safety limit')
        return body,r.url

def sha(b):return hashlib.sha256(b).hexdigest()

def col(df, names):
    found={re.sub('[^a-z0-9]','',str(x).lower()):x for x in df.columns}
    for name in names:
        v=found.get(re.sub('[^a-z0-9]','',name.lower()))
        if v is not None:return v
    return None

def canon_dates(x):
    x=x.astype(str).str.strip()
    try:return pd.to_datetime(x,format='mixed',errors='coerce').dt.strftime('%Y-%m-%d')
    except Exception:return pd.to_datetime(x,errors='coerce').dt.strftime('%Y-%m-%d')

def read_issuer_csv(path,forced):
    d=pd.read_csv(path,dtype=str,keep_default_na=False)
    dc=col(d,['ex_date','exdate','ex_dividend_date','ex-date','date'])
    ac=col(d,['cash_amount','distribution_per_share','total_distribution','dividend','amount','distribution'])
    tc=col(d,['ticker','symbol'])
    if dc is None or ac is None:raise ValueError('issuer CSV needs ex_date and cash_amount columns')
    ticker=d[tc].str.strip().str.upper() if tc else pd.Series(forced,index=d.index)
    if tc is None and forced is None:raise ValueError('issuer_actions.csv requires ticker column')
    e=pd.DataFrame({'ticker':ticker,'ex_date':canon_dates(d[dc]),
                    'amount':pd.to_numeric(d[ac].str.replace(r'[$,]','',regex=True),errors='coerce')})
    e=e[e.ticker.isin(TICKERS)]
    if e.ex_date.isna().any() or e.amount.isna().any():raise ValueError('invalid issuer CSV dates/amounts')
    # Dividend components may share ex-date. Sum only if original issuer explicitly
    # supplied already-total distribution; treat differing duplicates as ambiguous.
    conflicts=e.groupby(['ticker','ex_date']).amount.nunique()
    ambiguous={(str(t),str(x)) for t,x in conflicts[conflicts>1].index}
    e=e.drop_duplicates(['ticker','ex_date','amount'])
    e['source']='USER_SUPPLIED_ISSUER_CSV_PROVENANCE_UNVERIFIED'
    return e,ambiguous

def html_to_text(body):
    s=body.decode('utf-8','replace')
    s=re.sub(r'<script\b[^>]*>.*?</script>',' ',s,flags=re.I|re.S)
    s=re.sub(r'<style\b[^>]*>.*?</style>',' ',s,flags=re.I|re.S)
    s=re.sub(r'<[^>]+>',' ',s)
    return html.unescape(re.sub(r'\s+',' ',s))

def issuer_recent_blackrock(body,ticker):
    # Parse ONLY fund Distributions table. Search after Distributions section and
    # before Fees rather than matching unrelated dates elsewhere on page.
    txt=html_to_text(body)
    start=txt.find(' Distributions Schedule')
    if start<0:start=txt.find(' Distributions ')
    if start<0:return pd.DataFrame(columns=['ticker','ex_date','amount','source']), 'COULD_NOT_LOCATE_DISTRIBUTION_TABLE'
    segment=txt[start:]
    marker=re.search(r'\bRecord Date\s+Ex-Date\s+Payable Date\s+Total Distribution\b',segment,re.I)
    if not marker:return pd.DataFrame(columns=['ticker','ex_date','amount','source']), 'NO_PUBLIC_DISTRIBUTION_TABLE_FOUND'
    segment=segment[marker.end():]
    end=segment.find(' Fees ')
    if end>0:segment=segment[:end]
    # Record date, ex-date, payable date, total distribution.
    pattern=(r'([A-Z][a-z]{2} \d{2}, \d{4})\s+'
             r'([A-Z][a-z]{2} \d{2}, \d{4})\s+'
             r'([A-Z][a-z]{2} \d{2}, \d{4})\s+'
             r'\$\s*([0-9]+(?:\.[0-9]+)?)')
    items=[]
    for r in re.finditer(pattern,segment):
        try:date=dt.datetime.strptime(r.group(2),'%b %d, %Y').strftime('%Y-%m-%d')
        except ValueError:continue
        items.append({'ticker':ticker,'ex_date':date,'amount':float(r.group(4)),
                      'source':'BLACKROCK_OFFICIAL_VISIBLE_WEB_TABLE'})
    frame=pd.DataFrame(items,columns=['ticker','ex_date','amount','source']).drop_duplicates()
    # Paged web tables are not complete histories.
    return frame, 'PARTIAL_FIRST_PAGE_ONLY' if len(frame) else 'HTML_PARSE_NO_EVENTS'

def issuer_spdr_xlsx_from_page(body):
    s=body.decode('utf-8','replace')
    links=re.findall(r'<a\b([^>]*?)>(.*?)</a>',s,flags=re.I|re.S)
    choices=[]
    for attrs,title in links:
        desc=html.unescape(re.sub('<[^>]+>',' ',title)).lower()
        match=re.search(r'\bhref\s*=\s*["\']([^"\']+)',attrs,re.I)
        if match and ('historical distributions' in desc or ('distribut' in desc and 'xlsx' in desc)):
            choices.append(html.unescape(match.group(1)))
    return choices

def parse_spdr_xlsx(data):
    # State Street's official workbook may change its sheet/column layout.
    # Import only when an unambiguous ticker/date/amount table is recognized.
    book=pd.read_excel(io.BytesIO(data),sheet_name=None,header=None)
    output=[];evidence=[]
    for sheet,frame in book.items():
        for header in range(min(15,len(frame))):
            x=frame.iloc[header].fillna('').astype(str).tolist()
            raw=[str(s).lower().strip() for s in x]
            tick=next((i for i,v in enumerate(raw) if v in ['ticker','symbol','fund ticker']),None)
            ex=next((i for i,v in enumerate(raw) if v in ['ex-date','ex date','exdate','ex-dividend date']),None)
            amt=next((i for i,v in enumerate(raw) if v in ['distribution ($)','distribution','total distribution','total distribution ($)','distribution per share']),None)
            if tick is None or ex is None or amt is None:continue
            d=frame.iloc[header+1:].copy()
            for vals in d.itertuples(index=False,name=None):
                t=str(vals[tick]).strip().upper()
                if t!='SPY':continue
                day=pd.to_datetime(vals[ex],errors='coerce')
                if pd.isna(day):continue
                amount=pd.to_numeric(str(vals[amt]).replace('$','').replace(',',''),errors='coerce')
                if pd.isna(amount) or float(amount)<0:continue
                output.append({'ticker':'SPY','ex_date':day.strftime('%Y-%m-%d'),'amount':float(amount),
                               'source':'STATE_STREET_OFFICIAL_XLSX'})
            evidence.append({'sheet':sheet,'header_row':header+1,'parsed_spy_events':len(output)})
            break
    return pd.DataFrame(output,columns=['ticker','ex_date','amount','source']).drop_duplicates(), evidence

def get_official(offline,out):
    observations=[];states={};docs=[]
    for ticker,url in ISSUER_URLS.items():
        state={'page_url':url,'status':'UNVERIFIED','events_found':0,'completeness':'UNKNOWN'}
        cache=out/f'official_{ticker}_page.html'
        try:
            if not offline:
                b,_=get(url)
                if not b.lstrip().lower().startswith((b'<!doctype',b'<html')):raise ValueError('Not an HTML page')
                cache.write_bytes(b)
            else:
                if not cache.exists():raise ValueError('Offline and no saved issuer page')
                b=cache.read_bytes()
            state['page_sha256']=sha(b)
            if ticker in ('TLT','HYG'):
                frame,msg=issuer_recent_blackrock(b,ticker)
                state.update(status=msg,events_found=len(frame),completeness='PARTIAL' if len(frame) else 'UNKNOWN')
                if len(frame):observations.append(frame)
            else:
                hrefs=issuer_spdr_xlsx_from_page(b)
                state['xlsx_links_discovered']=len(hrefs)
                for h in hrefs[:2]:
                    from urllib.parse import urljoin
                    absolute=urljoin(url,h)
                    if not absolute.lower().startswith('https://'):continue
                    try:
                        if offline:
                            xfile=out/'official_SPY_distributions.xlsx'
                            if not xfile.exists():continue
                            dat=xfile.read_bytes()
                        else:
                            dat,_=get(absolute,max_bytes=25_000_000)
                            if not dat.startswith(b'PK'):raise ValueError('Not XLSX')
                            (out/'official_SPY_distributions.xlsx').write_bytes(dat)
                        frame,sheets=parse_spdr_xlsx(dat)
                        state.update(status='OFFICIAL_XLSX_PARSED' if len(frame) else 'OFFICIAL_XLSX_NO_RECOGNIZED_DATA',
                                     events_found=len(frame),download_url=absolute,xlsx_sha256=sha(dat),sheets=sheets,
                                     completeness='CHECK_XLSX_HISTORICAL_RANGE' if len(frame) else 'UNKNOWN')
                        if len(frame):observations.append(frame)
                        break
                    except Exception as exc:
                        state['xlsx_download_error']=str(exc)[:180]
                if state['status']=='UNVERIFIED':state['status']='NO_PARSEABLE_OFFICIAL_XLSX'
        except Exception as exc:state.update(status='OFFICIAL_ACCESS_UNAVAILABLE',error=str(exc)[:180])
        states[ticker]=state
    paths=[(ISSUER/f'issuer_{x}.csv',x) for x in TICKERS]+[(ISSUER/'issuer_actions.csv',None)]
    for path,forced in paths:
        if not path.exists():continue
        try:
            d,amb=read_issuer_csv(path,forced)
            observations.append(d)
            docs.append({'path':str(path),'sha256':sha(path.read_bytes()),'status':'FILE_CONTENT_PARSED_ORIGIN_NOT_VERIFIED',
                         'ambiguous_date_amounts':sorted([list(x) for x in amb])})
        except Exception as exc:docs.append({'path':str(path),'status':'FILE_PARSE_ERROR','error':str(exc)})
    result=pd.concat(observations,ignore_index=True) if observations else pd.DataFrame(columns=['ticker','ex_date','amount','source'])
    result.to_csv(out/'official_and_supplied_issuer_events.csv',index=False)
    return result,states,docs

def yahoo_cached(ticker):
    path=OLD/f'yahoo_{ticker}_chart.json'
    if not path.exists():return None,f'MISSING_SECONDARY_CACHE: {path}'
    try:
        doc=json.loads(path.read_text(encoding='utf-8'))['chart']['result'][0]
        d=doc['indicators'];quote=d['quote'][0]
        tz=pd.to_datetime(doc['timestamp'],unit='s',utc=True).tz_convert('America/New_York')
        adj=d.get('adjclose') or []
        adjclose=adj[0].get('adjclose') if adj else None
        x=pd.DataFrame({'session':tz.strftime('%Y-%m-%d'),'secondary_close':quote.get('close'),
                        'secondary_open':quote.get('open'),
                        'secondary_adjusted_close':adjclose if adjclose is not None else [np.nan]*len(tz)})
        x=x.drop_duplicates('session').sort_values('session')
        ev=[]
        for i in (doc.get('events') or {}).get('dividends',{}).values():
            date=dt.datetime.fromtimestamp(int(i['date']),dt.timezone.utc).strftime('%Y-%m-%d')
            ev.append({'ex_date':date,'amount':float(i['amount'])})
        splits=[]
        for i in (doc.get('events') or {}).get('splits',{}).values():
            date=dt.datetime.fromtimestamp(int(i['date']),dt.timezone.utc).strftime('%Y-%m-%d')
            splits.append({'ticker':ticker,'date':date,'ratio':i.get('splitRatio'),'source':'YAHOO_SECONDARY'})
        return (x,pd.DataFrame(ev),pd.DataFrame(splits)), 'YAHOO_CACHE_SECONDARY_NOT_ISSUER'
    except Exception as exc:return None,f'CORRUPT_SECONDARY_CACHE: {exc}'

def local_daily(ticker,epoch):
    path=OVERNIGHT/f'overnight_etf_{ticker}_{epoch}.csv.gz'
    if not path.exists():raise FileNotFoundError(f'3.7 output missing: {path}')
    df=pd.read_csv(path,usecols=['previous_session','session','prior_last_bar_close','next_first_bar_open','etf_status'])
    close=df[['previous_session','prior_last_bar_close']].rename(columns={'previous_session':'session','prior_last_bar_close':'local_close'})
    # 3.7 has one close per PREVIOUS session; first/last outside source may be null
    close=close.dropna(subset=['local_close']).drop_duplicates('session').sort_values('session')
    close['session']=close.session.astype(str).str[:10]
    close.local_close=pd.to_numeric(close.local_close,errors='coerce')
    close=close[np.isfinite(close.local_close)&(close.local_close>0)]
    return close

def math_scores(local,secondary,exdates):
    full=local.merge(secondary,on='session',how='inner').sort_values('session')
    for name in ['secondary_close','secondary_adjusted_close']:
        full[name]=pd.to_numeric(full[name],errors='coerce')
    full=full[(full.secondary_close>0)&(full.secondary_adjusted_close>0)].copy()
    if len(full)<30:return {'status':'INSUFFICIENT_ADJUSTED_SECONDARY_DATA','matched_days':len(full)},pd.DataFrame()
    # Ratios and their first differences are robust to constant series scaling.
    full['ratio_raw_bp']=1e4*np.log(full.local_close/full.secondary_close)
    full['ratio_adj_bp']=1e4*np.log(full.local_close/full.secondary_adjusted_close)
    full['ratio_raw_change_bp']=full.ratio_raw_bp.diff()
    full['ratio_adj_change_bp']=full.ratio_adj_bp.diff()
    full['date_gap_days']=pd.to_datetime(full.session).diff().dt.days
    # compare only neighboring observed trading sessions; 1-4 day gaps avoid many holidays,
    # but 4 days can span a missing session so label diagnostic only.
    consecutive=full.date_gap_days.between(1,4)
    event=full.session.isin(exdates)&consecutive
    def quant(s):
        s=pd.to_numeric(s,errors='coerce'); s=s[np.isfinite(s)]
        return {'n':int(len(s)),'median_abs_bp':round(float(np.median(np.abs(s))),4) if len(s) else None,
                'p90_abs_bp':round(float(np.percentile(np.abs(s),90)),4) if len(s) else None}
    score={'status':'DIAGNOSTIC_NOT_CERTIFICATION','matched_days':len(full),
           'raw_level_ratios':quant(full.ratio_raw_bp),
           'adjusted_level_ratios':quant(full.ratio_adj_bp),
           'all_adjacent_raw_ratio_changes':quant(full.loc[consecutive,'ratio_raw_change_bp']),
           'all_adjacent_adj_ratio_changes':quant(full.loc[consecutive,'ratio_adj_change_bp']),
           'exdate_raw_ratio_changes':quant(full.loc[event,'ratio_raw_change_bp']),
           'exdate_adj_ratio_changes':quant(full.loc[event,'ratio_adj_change_bp']),
           'conclusion':'Neither daily prices nor vendor documentation proves HF preserved PiTrading adjustment basis.'}
    return score,full

def transition_test(ticker,legacy,modern,secondary):
    left=legacy[legacy.session=='2022-03-04']
    right=modern[modern.session=='2022-03-07']
    sy=secondary.set_index('session')
    result={'ticker':ticker,'last_legacy_session':'2022-03-04','first_raw_session':'2022-03-07',
            'status':'INSUFFICIENT_BOUNDARY_ENDPOINTS','cross_vendor_return_policy':'DO_NOT_CONSTRUCT'}
    if len(left)==0 or len(right)==0:return result
    lp=float(left.iloc[0].local_close);rp=float(right.iloc[0].local_close)
    result['legacy_close_2022_03_04']=lp;result['raw_close_2022_03_07']=rp
    result['naive_cross_vendor_close_to_close_bp']=round(1e4*math.log(rp/lp),3)
    if not {'2022-03-04','2022-03-07'}.issubset(set(sy.index)):
        result['status']='MISSING_SECONDARY_BOUNDARY';return result
    a=sy.loc['2022-03-04'];b=sy.loc['2022-03-07']
    if a.secondary_close>0 and b.secondary_close>0:
        result['secondary_raw_close_to_close_bp']=round(1e4*math.log(b.secondary_close/a.secondary_close),3)
        result['cross_vendor_artificial_difference_bp']=round(result['naive_cross_vendor_close_to_close_bp']-result['secondary_raw_close_to_close_bp'],3)
        result['last_legacy_level_ratio_to_yahoo_raw']=round(lp/a.secondary_close,7)
        result['first_modern_level_ratio_to_yahoo_raw']=round(rp/b.secondary_close,7)
        result['status']='MEASURED_LEVEL_DISCONTINUITY_NOT_A_SYNTHETIC_RETURN'
    return result

def self_test():
    # Synthetic adjusting/discontinuous examples with known answers.
    base=pd.DataFrame({'session':['2022-03-04','2022-03-07'],'secondary_close':[100.,101.],
                       'secondary_adjusted_close':[90.,91.]})
    legacy=pd.DataFrame({'session':['2022-03-04'],'local_close':[90.]})
    raw=pd.DataFrame({'session':['2022-03-07'],'local_close':[101.]})
    test=transition_test('SPY',legacy,raw,base)
    assert test['cross_vendor_artificial_difference_bp']>900
    d=pd.DataFrame({'ticker':['SPY'],'ex_date':['2026-09-18'],'amount':[1.23]})
    assert len(d[d.ex_date=='2026-09-18'])==1
    a=pd.DataFrame({'session':['2020-01-02','2020-01-03','2020-01-06'], 'local_close':[50,51,52]})
    b=pd.DataFrame({'session':['2020-01-02','2020-01-03','2020-01-06'], 'secondary_close':[100,102,104],
                    'secondary_adjusted_close':[50,51,52]})
    score,_=math_scores(a,b,{'2020-01-03'})
    assert score['status']=='INSUFFICIENT_ADJUSTED_SECONDARY_DATA'  # threshold must reject tiny sample
    print('SELF-TEST PASS: boundary discontinuity, secondary basis calculation, event matching, small-sample safeguard')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--offline',action='store_true');ap.add_argument('--self-test',action='store_true')
    ap.add_argument('--out',type=Path,default=OUT)
    args=ap.parse_args()
    self_test()
    if args.self_test:return
    out=args.out.expanduser();out.mkdir(parents=True,exist_ok=True)
    official,official_states,manual_files=get_official(args.offline,out)
    old_ref=OLD/'candidate_dividends_all_epochs.csv'
    if not old_ref.exists():raise FileNotFoundError(f'First run 3.8 full verification: missing {old_ref}')
    candidates=pd.read_csv(old_ref)
    candidates=candidates[candidates.ticker.isin(TICKERS)].copy()
    candidates.ex_date=candidates.ex_date.astype(str).str[:10]
    # Preserve original amount source priority but do not overwrite with partial issuer records.
    prior_old=OLD/'section2_vs_secondary_event_comparison.csv'
    comparison=pd.read_csv(prior_old) if prior_old.exists() else pd.DataFrame()
    matches=[]
    for rec in official.itertuples(index=False):
        try:
            ref=candidates[(candidates.ticker==rec.ticker)&(candidates.ex_date==rec.ex_date)]
            if not len(ref):status='ISSUER_DATE_NOT_IN_CANDIDATES';delta=None
            else:
                delta=round(float(abs(float(ref.iloc[0].amount)-rec.amount)),6)
                status='AMOUNT_MATCH_0_005USD' if delta<=.005 else 'AMOUNT_DISAGREEMENT'
            matches.append({'ticker':rec.ticker,'ex_date':rec.ex_date,'issuer_amount':rec.amount,
                            'reference_amount':float(ref.iloc[0].amount) if len(ref) else None,
                            'absolute_difference':delta,'status':status,'source':rec.source})
        except Exception as exc:matches.append({'ticker':str(rec.ticker),'status':'PARSE_ERROR','error':str(exc)})
    md=pd.DataFrame(matches,columns=['ticker','ex_date','issuer_amount','reference_amount','absolute_difference','status','source'])
    md.to_csv(out/'issuer_vs_reference_checks.csv',index=False)
    # Published vendor policy: official PiTrading page declares stock/ETF data adjusted for splits and dividends.
    vendor={'url':PITRADING_URL,'claim':'PiTrading stock/ETF price data adjusted for corporate actions including dividends and splits',
            'web_documentation_known':'PUBLIC_VENDOR_PAGE','status':'WEB_PAGE_NOT_REFETCHED',
            'hf_preservation_of_vendor_adjustments':'NOT_VERIFIED'}
    if not args.offline:
        try:
            body,finalurl=get(PITRADING_URL);page=html_to_text(body).lower()
            vendor['status']='CLAIM_PRESENT_ON_LIVE_WEBPAGE' if ('adjusted for corporate actions' in page and 'dividends' in page) else 'CLAIM_NOT_FOUND_ON_LIVE_PAGE'
            vendor['page_sha256']=sha(body);vendor['retrieved_url']=finalurl
        except Exception as exc:vendor.update(status='LIVE_VENDOR_FETCH_UNAVAILABLE',error=str(exc)[:180])
    legacy_rows=[];transition_rows=[];splits=[];events_by_asset={};statuses={}
    for ticker in TICKERS:
        y,ystatus=yahoo_cached(ticker);statuses[ticker]=ystatus
        if y is None:
            legacy_rows.append({'ticker':ticker,'status':ystatus});transition_rows.append({'ticker':ticker,'status':ystatus})
            continue
        secondary,y_events,y_splits=y
        if len(y_splits):splits.extend(y_splits.to_dict('records'))
        eventdates=set(candidates[(candidates.ticker==ticker)&(candidates.ex_date<SWITCH)].ex_date)
        leg=local_daily(ticker,'LEGACY');mod=local_daily(ticker,'RAW')
        score,detail=math_scores(leg,secondary,eventdates)
        score['ticker']=ticker;score['independently_reported_secondary_splits']=len(y_splits)
        legacy_rows.append(score)
        if len(detail):
            chosen=detail[(detail.session.isin(eventdates)) | (detail.session.between('2022-02-21','2022-03-07'))]
            chosen.to_csv(out/f'legacy_exdate_price_basis_{ticker}.csv',index=False)
        transition_rows.append(transition_test(ticker,leg,mod,secondary))
        events_by_asset[ticker]={'provisional_dividends_from_prev_audit':int((candidates.ticker==ticker).sum()),
                                 'secondary_event_count':int(len(y_events)),
                                 'official_observed_count':int((official.ticker==ticker).sum()),
                                 'full_issuer_history_certified':False}
        print(f'  {ticker}: legacy matched {score.get("matched_days","?")} days; issuer events {int((official.ticker==ticker).sum())}',flush=True)
    pd.DataFrame(splits,columns=['ticker','date','ratio','source']).to_csv(out/'all_secondary_reported_splits.csv',index=False)
    pd.DataFrame(legacy_rows).to_csv(out/'legacy_price_basis_results.csv',index=False)
    pd.DataFrame(transition_rows).to_csv(out/'transition_2022_results.csv',index=False)
    official_status={}
    for t in TICKERS:
        z=md[md.ticker==t]
        official_status[t]={'official_dates_compared':len(z),
                            'matching':int((z.status=='AMOUNT_MATCH_0_005USD').sum()),
                            'mismatches':int((z.status=='AMOUNT_DISAGREEMENT').sum()),
                            'not_in_candidate_reference':int((z.status=='ISSUER_DATE_NOT_IN_CANDIDATES').sum()),
                            'issuer_full_historical_coverage':'NOT_CERTIFIED',
                            'retrieval':official_states[t]}
    outcomes={'section':'3.8 last four checks','execution_date_local':dt.datetime.now().astimezone().isoformat(timespec='seconds'),
             'vendor_pi_trading_adjustment_documentation':vendor,
             '1_dividends_issuer':official_status,
             '2_historical_dividends':events_by_asset,
             '3_legacy_price_basis_empirical':legacy_rows,
             '4_stock_splits':{'secondary_reported':splits,
                                'issuer_full_history_split_completeness':'NOT_CERTIFIED'},
             '5_2022_source_transition':transition_rows,
             'manual_issuer_files':manual_files,
             'secondary_reference_status':statuses,
             'original_prices_modified':False,
             'next_decision':('Use documented PiTrading adjustment claim plus empirical tests; do not apply historical cash dividends automatically. '
                              'If no complete issuer files available, document issuer completeness as unverified and do not hold up subsequent modeling indefinitely.')}
    (out/'summary.json').write_text(json.dumps(outcomes,indent=2,default=str),encoding='utf-8')
    s=[]
    s+=['# Section 3.8 — Final four checks','',
         '**Read-only verification. No ETF price bars, dividends, or old reports were modified.**','',
         '## 1. Issuer dividend and historical completeness']
    for t in TICKERS:
        v=official_status[t];s.append(f'- {t}: {v["official_dates_compared"]} official/supplied events parsed; {v["matching"]} date/amount matches; {v["mismatches"]} amount mismatches; {v["not_in_candidate_reference"]} newly revealed dates. Status: {v["retrieval"]["status"]}. Historical completeness: NOT VERIFIED.')
    s+=['','**WARNING:** iShares public site may expose only ten paginated entries. No conclusion of completeness follows from partial issuer verification. Manually named issuer files without provenance are not certified.','',
         '## 2. PiTrading source adjustment basis',
         f'- Public PiTrading documentation says dividend- and split-adjusted bars; live retrieval status: **{vendor["status"]}**.',
         '- Whether HF preserved these adjustments, whether they are retrospective as-of-2026, and exact ex-date basis remain NOT VERIFIED. Do NOT add legacy cash distributions to legacy return without evidence.','',
         '## 3. Empirical historical price-basis comparison']
    for rec in legacy_rows:
        t=rec['ticker']; raw=rec.get('exdate_raw_ratio_changes',{});adj=rec.get('exdate_adj_ratio_changes',{})
        s.append(f'- {t}: {rec.get("matched_days",0)} matched days; ex-date median absolute local/Yahoo raw-ratio change {raw.get("median_abs_bp","n/a")} bp vs local/Yahoo adjusted-ratio change {adj.get("median_abs_bp","n/a")} bp. Diagnostic, NOT proof.')
    s+=['','## 4. Splits','- Secondary Yahoo reported '+str(len(splits))+' split records. Complete official issuer split history NOT VERIFIED.','',
         '## 5. March 2022 transition']
    for rec in transition_rows:
        s.append(f'- {rec["ticker"]}: {rec.get("status")}; naive cross-vendor close-close {rec.get("naive_cross_vendor_close_to_close_bp","n/a")} bp; secondary daily raw {rec.get("secondary_raw_close_to_close_bp","n/a")} bp. Artificial difference {rec.get("cross_vendor_artificial_difference_bp","n/a")} bp.')
    s+=['','## Rules for analysis','- Keep legacy and modern observed returns in separate provenance epochs; combining percentages is possible, but do not fabricate the boundary return.',
         '- Use modern RAW price returns and predeclared modern cash-adjusted ex-date overnight estimates; historical dividends remain UNADJUSTED by us because source prices appear to be adjusted already.',
         '- For academic claims, label total-return convention and back-adjustment look-ahead/point-in-time limitations.',
         '- Preserve uncertainty where issuer sources are incomplete.','',
         '## Files','- summary.json, issuer_vs_reference_checks.csv, legacy_price_basis_results.csv, transition_2022_results.csv, legacy_exdate_price_basis_*.csv.','']
    (out/'REPORT.md').write_text('\n'.join(s),encoding='utf-8')
    print(f'SUCCESS: {out}')
    print('Upload REPORT.md, summary.json, issuer_vs_reference_checks.csv, legacy_price_basis_results.csv and transition_2022_results.csv.')

if __name__=='__main__':main()
