"""Section 2 targeted follow-up for SPY/TLT/HYG, October 2026.

Run: pip install pandas numpy pandas_market_calendars
     python section2_targeted_remaining_checks.py

Uses VERIFIED PATHS in the user's Section 2 REPORT.md, with location fallbacks.
No source files changed. Results in section2_followup_results/ next to script.

What this CAN prove: annual/time-of-day completeness, cross-asset missingness,
RAW-vs-CLEAN deleted timestamps, session label checks, overnight endpoint availability.
What it CANNOT prove: why a RAW minute has no IEX trades; PiTrading's historical
look-ahead logic; DXY constituent weights; historical adjustment as-of conventions.
"""
from pathlib import Path
import hashlib
import io
import json
import zipfile
import warnings

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal

HOME = Path.home()
RAW_DIR = HOME / 'OneDrive' / 'Desktop' / 'data' / 'raw'
DOWNLOADS = HOME / 'Downloads'
OUT = Path(__file__).resolve().parent / 'section2_followup_results'
OUT.mkdir(parents=True, exist_ok=True)

FILES = {
    'SPY_LEGACY': [RAW_DIR / 'SPY_clean_1min.csv'],
    'TLT_LEGACY': [RAW_DIR / 'TLT_clean_1min.csv'],
    'HYG_LEGACY': [RAW_DIR / 'HYG_clean_1min.csv'],
    'SPY_RAW': [DOWNLOADS / 'hfdatalibrary_raw_1min_1tickers_2026-10-13.zip', RAW_DIR / 'hf_raw' / 'SPY_raw_1min.csv'],
    'TLT_RAW': [RAW_DIR / 'hf_raw' / 'TLT_raw_1min.csv'],
    'HYG_RAW': [RAW_DIR / 'hf_raw' / 'HYG_raw_1min.csv'],
    'SPY_CLEAN': [DOWNLOADS / 'hfdatalibrary_clean_1min_5tickers_2026-10-03.zip'],
    'TLT_CLEAN': [DOWNLOADS / 'hfdatalibrary_clean_1min_5tickers_2026-10-03.zip'],
    'HYG_CLEAN': [DOWNLOADS / 'hfdatalibrary_clean_1min_5tickers_2026-10-03.zip'],
}
# IMPORTANT: The old CLEAN archive dated October 3 and the newer RAW archive
# dated October 13 have different dividend price adjustment conventions.
# Timestamp comparisons remain valid; raw price-level comparisons are NOT comparable.

PRE_CUTOFF = pd.Timestamp('2022-03-07')
SOURCE_WINDOW_END = pd.Timestamp('2026-10-02') # exclusive; common RAW/CLEAN period
CAL = mcal.get_calendar('NYSE')


def sha256(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for buf in iter(lambda:f.read(8*1024*1024),b''):
            h.update(buf)
    return h.hexdigest()


def resolve(key):
    for p in FILES[key]:
        if p.exists(): return p
    raise FileNotFoundError(f'{key}: none of the expected files exists: {FILES[key]}')


def load(key):
    path = resolve(key)
    asset = key.split('_')[0]
    if path.suffix.lower() == '.zip':
        member=f'{asset}_{key.split("_")[-1].lower()}_1min.csv'
        with zipfile.ZipFile(path) as z:
            if member not in z.namelist():
                found=[x for x in z.namelist() if Path(x).name.lower()==member.lower()]
                if not found: raise ValueError(f'{member} not found inside {path}')
                member=found[0]
            df=pd.read_csv(io.BytesIO(z.read(member)),usecols=['datetime','Open','Close','Volume','source'])
    else:
        df=pd.read_csv(path,usecols=['datetime','Open','Close','Volume','source'])
    d=pd.to_datetime(df['datetime'],errors='coerce')
    if d.isna().any(): raise ValueError(f'{key} has {int(d.isna().sum())} malformed dates')
    if d.dt.tz is not None:
        d=d.dt.tz_convert('America/New_York').dt.tz_localize(None)
    df['datetime']=d
    dup=int(df['datetime'].duplicated().sum())
    if dup: raise ValueError(f'{key}: {dup} duplicated timestamps; inspect before deduplication')
    df=df.set_index('datetime').sort_index()
    if key.endswith('LEGACY'): df=df.loc[df.index < PRE_CUTOFF]
    if key.endswith('RAW') or key.endswith('CLEAN'):
        df=df.loc[(df.index >= PRE_CUTOFF) & (df.index < SOURCE_WINDOW_END)]
    return df, path


def grid_index(start,end):
    schedule=CAL.schedule(start_date=start.date(),end_date=end.date())
    arrays=[]; session_map=[]
    for _, r in schedule.iterrows():
        start_ny=r['market_open'].tz_convert('America/New_York').tz_localize(None)
        end_ny=r['market_close'].tz_convert('America/New_York').tz_localize(None)
        arr=pd.date_range(start_ny,end_ny-pd.Timedelta(minutes=1),freq='min')
        if len(arr):
            arrays.append(arr)
            session_map.extend([start_ny.date()]*len(arr))
    if not arrays: return pd.DatetimeIndex([]),pd.Index([])
    return arrays[0].append(arrays[1:]),pd.Index(session_map)


def make_presence(df):
    expected, days=grid_index(df.index.min(),df.index.max())
    presence=pd.Series(True,index=df.index).reindex(expected).fillna(False).astype(bool)
    return presence,days


def year_hour_table(presence,key):
    minutes=presence.index.hour*60+presence.index.minute - 570
    interval=pd.cut(minutes, bins=[-1,29,119,299,389], labels=['09:30-09:59','10:00-11:29','11:30-14:29','14:30-15:59'])
    x=pd.DataFrame({'year':presence.index.year,'period':interval.astype(str),'present':presence.values})
    yearly=x.groupby('year',sort=True)['present'].agg(['sum','count','mean']).reset_index()
    yearly['key']=key
    by_time=x.groupby(['year','period'],sort=True)['present'].agg(['sum','count','mean']).reset_index()
    by_time['key']=key
    return yearly,by_time


def gap_stats(presence):
    if not len(presence): return dict(missing=0, gap_runs=0)
    missing=~presence
    # Group missing minutes WITHIN a single NYSE session only; never merge across days.
    day=pd.Index(presence.index.date)
    is_new=day.to_series(index=presence.index).ne(day.to_series(index=presence.index).shift())
    group=(missing.ne(missing.shift(fill_value=False))|is_new).cumsum()
    sizes=missing.groupby(group).sum()
    sizes=sizes[sizes>0]
    return dict(missing=int(missing.sum()),gap_runs=int(len(sizes)),single=int((sizes==1).sum()),two_to_five=int(((sizes>=2)&(sizes<=5)).sum()),over_five=int((sizes>5).sum()),max_length=int(sizes.max()) if len(sizes) else 0)


def snapshot_joint(presences, keys):
    common=presences[keys[0]].index
    for k in keys[1:]: common=common.intersection(presences[k].index)
    if common.empty:return None
    a=np.column_stack([presences[k].reindex(common).fillna(False).to_numpy(dtype=bool) for k in keys])
    return {'keys':keys,'expected':int(len(common)),'all_present':int(a.all(axis=1).sum()),'all_present_pct':float(100*a.all(axis=1).mean()), 'none_present':int((~a.any(axis=1)).sum())}


def compare_clean(raw,clean,asset):
    start=max(raw.index.min(),clean.index.min())
    end=min(raw.index.max(),clean.index.max())
    raw_ix=raw.loc[start:end].index
    clean_ix=clean.loc[start:end].index
    removed=raw_ix.difference(clean_ix)
    added=clean_ix.difference(raw_ix)
    return {'asset':asset,'common_first':str(start),'common_last':str(end),'raw_rows_in_common_span':int(len(raw_ix)),'clean_rows_in_common_span':int(len(clean_ix)),'removed_raw_timestamps':int(len(removed)),'removed_pct_of_raw':100*len(removed)/len(raw_ix) if len(raw_ix) else None,'added_clean_timestamps':int(len(added)),'price_level_comparison':'INVALID across Oct-06-2026 archive vintages'}


def overnight_endpoints(df,asset):
    # A day contributes a valid overnight ETF price return only if the LAST minute
    # close exists on prior NYSE session and FIRST minute open exists on next session.
    first=df.index.min(); last=df.index.max()
    sched=CAL.schedule(start_date=first.date(),end_date=last.date())
    days=[]
    for date,r in sched.iterrows():
        opening=r['market_open'].tz_convert('America/New_York').tz_localize(None)
        closing=r['market_close'].tz_convert('America/New_York').tz_localize(None)
        days.append((str(date.date()),opening,closing-pd.Timedelta(minutes=1)))
    rows=[]
    for i in range(1,len(days)):
        previous,opening_day=days[i-1],days[i]
        prev_close=previous[2]; current_open=opening_day[1]
        prior_good=prev_close in df.index
        open_good=current_open in df.index
        price_return=None
        if prior_good and open_good:
            cp=df.loc[prev_close,'Close']; op=df.loc[current_open,'Open']
            if cp>0 and op>0:price_return=float(np.log(op/cp))
        rows.append({'asset':asset,'from_date':previous[0],'to_date':opening_day[0],
                     'prev_close_bar':str(prev_close),'next_open_bar':str(current_open),
                     'gap_hours':(current_open-(prev_close+pd.Timedelta(minutes=1))).total_seconds()/3600,
                     'both_endpoint_bars_available':bool(prior_good and open_good),'log_price_return':price_return})
    return pd.DataFrame(rows)


def main():
    original_files={}; data={}; presences={}; yearly=[]; tod=[]; bad=[]
    print('Section 2: targeted follow-up (read-only)')
    for key in FILES:
        try:
            df,path=load(key)
            tags=df['source'].astype(str).value_counts().to_dict()
            # Retain only the two price fields needed for overnight endpoint tests.
            # The original input remains untouched; this reduces peak memory use.
            df=df[['Open','Close']]
            data[key]=df
            p,days=make_presence(df)
            presences[key]=p
            y,t=year_hour_table(p,key);yearly.append(y);tod.append(t)
            original_files[key]={'file':str(path),'sha256':sha256(path),'rth_presence':int(p.sum()),'expected_minutes':len(p),'coverage_pct':100*p.mean(),'source_tags':tags}
            print(f'{key:11} rows={len(df):>8,} coverage={p.mean()*100:6.2f}%')
        except Exception as e:
            bad.append({'key':key,'error':repr(e)})
            print(f'{key}: ERROR {e}')

    if not data: raise RuntimeError('No files loaded. Verify paths listed at top of script.')
    if yearly:pd.concat(yearly,ignore_index=True).to_csv(OUT/'coverage_by_year.csv',index=False)
    if tod:pd.concat(tod,ignore_index=True).to_csv(OUT/'coverage_by_year_and_session_time.csv',index=False)
    comparisons=[]
    for asset in ['SPY','TLT','HYG']:
        raw=f'{asset}_RAW';clean=f'{asset}_CLEAN'
        if raw in data and clean in data:
            comparisons.append(compare_clean(data[raw],data[clean],asset))

    snapshots=[]
    for name, ks in [
        ('legacy SPY-TLT',['SPY_LEGACY','TLT_LEGACY']),
        ('legacy SPY-HYG',['SPY_LEGACY','HYG_LEGACY']),
        ('legacy SPY-TLT-HYG',['SPY_LEGACY','TLT_LEGACY','HYG_LEGACY']),
        ('raw SPY-TLT-HYG',['SPY_RAW','TLT_RAW','HYG_RAW']),
        ('clean SPY-TLT-HYG',['SPY_CLEAN','TLT_CLEAN','HYG_CLEAN'])]:
        if all(k in presences for k in ks):
            x=snapshot_joint(presences,ks)
            if x: snapshots.append({'name':name,**x})

    gaps={k:gap_stats(p) for k,p in presences.items()}
    overnight=[]
    for asset in ['SPY','TLT','HYG']:
        for suffix in ['LEGACY','RAW']:
            k=f'{asset}_{suffix}'
            if k in data:
                o=overnight_endpoints(data[k],k)
                o.to_csv(OUT/f'overnight_endpoint_availability_{k}.csv',index=False)
                overnight.append({'key':k,'eligible':int(o['both_endpoint_bars_available'].sum()),'sessions_checked':len(o),'pct_with_endpoints':float(100*o['both_endpoint_bars_available'].mean()) if len(o) else None})

    out={'input_manifest':original_files,'load_failures':bad,'yearly_coverage_csv':'coverage_by_year.csv','session_time_coverage_csv':'coverage_by_year_and_session_time.csv',
         'gap_profiles':gaps,'cross_asset_overlap':snapshots,'raw_vs_old_clean_timestamp_deletions':comparisons,
         'overnight_endpoints':overnight,'still_requires_external_confirmation':[
         'Why any particular missing minute is absent (no IEX trade vs legacy vendor filter)',
         'Historical PiTrading cleaning uses future observations: not provable without raw or vendor explanation',
         'Exact original legacy corporate action adjustment/as-of convention',
         'Dukascopy dollar index weight composition and relationship to ICE DXY',
         'Validation of exact Dukascopy CSV timezone from download settings and provider',
         'ETF and quote candle label conventions; documentary evidence for both',
         'Finalize overnight returns and event-window eligibility in Section 3',
         'Check actual research event results after applying gap-aware rules, later sections'
         ]}
    (OUT/'summary.json').write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')
    lines=['# Section 2 targeted follow-up', '', 'Scope: complete missingness and alignment diagnostics, NOT final preprocessing/model evaluation.',
           '', '## Findings: coverage', '']
    for k,d in original_files.items():lines.append(f'- **{k}**: {d["coverage_pct"]:.2f}% RTH minutes ({d["rth_presence"]:,} / {d["expected_minutes"]:,}).')
    lines+=['','## Cross-asset overlaps','']
    for x in snapshots:lines.append(f'- {x["name"]}: {x["all_present_pct"]:.2f}% simultaneous minutes ({x["all_present"]:,}/{x["expected"]:,}).')
    lines+=['','## RAW vs OLD CLEAN timestamp removals','']
    for d in comparisons:lines.append(f'- {d["asset"]}: {d["removed_raw_timestamps"]:,} deleted RAW timestamps ({d["removed_pct_of_raw"]:.2f}%); added CLEAN {d["added_clean_timestamps"]}. Price *levels* cannot be compared between these two downloaded vintages.')
    lines+=['','## ETF overnight endpoint availability', '']
    for d in overnight:lines.append(f'- {d["key"]}: {d["eligible"]:,}/{d["sessions_checked"]:,} session pairs have both endpoint bars ({d["pct_with_endpoints"]:.2f}%).')
    lines+=['','## Known limitations / follow-ups','']
    lines += [f'- {x}' for x in out['still_requires_external_confirmation']]
    lines+=['','## Methodological caveats','',
            '- ETF gap rates mix no-trade minutes, feed gaps, and possible filter deletions. A missing minute is not inherently a data error.',
            '- As-of 2026-10-06 HF rebuilt prices to splits-only. Do NOT merge old CLEAN and new RAW price histories without harmonizing vintage.',
            '- A 9:30 bar timestamp is the START of that minute; do not assume the bar CLOSE is known at 9:30.',
            '- 15:59 bar CLOSE is only observable at the market close (16:00).',
            '- Overnight endpoint returns are log PRICE returns, not necessarily dividend-adjusted total returns.',
            '- The script reads but never modifies source files.', '',
            '## Output','', 'summary.json; coverage_by_year.csv; coverage_by_year_and_session_time.csv; overnight_endpoint_availability_*.csv']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\nSaved:',OUT)
    print('Open REPORT.md and share it + summary.json')

if __name__=='__main__':
    main()
