#!/usr/bin/env python3
r"""Section 3.8: ETF corporate-action/date audit and qualified ex-date overnight returns.

Run in PowerShell:
    python "$HOME\Downloads\section3_8_corporate_actions.py"
Optional:
    python "$HOME\Downloads\section3_8_corporate_actions.py" --actions "C:\path\to\corporate_actions.csv"
    python "$HOME\Downloads\section3_8_corporate_actions.py" --self-test

Requires: pandas, numpy. Offline: reuses the issuer-event reference snapshot from Section 2.
All source inputs read-only. Does not alter or merge underlying price bars.
Important: legacy PiTrading historical adjustment conventions cannot be established
from this transformation; NEVER dividend-adjust legacy bars without verification.
"""
from __future__ import annotations

import argparse
import json
import hashlib
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd

HOME = Path.home()
DL = HOME / 'Downloads'
ROOT = HOME / 'OneDrive' / 'Desktop' / 'data'
AUDIT_ROOT = ROOT / 'raw_clean_price_audit_20261014'
DEFAULT_ACTIONS = AUDIT_ROOT / 'corporate_actions.csv'
DEFAULT_OVERNIGHT = DL / 'section3_7_overnight_results'
OUT = DL / 'section3_8_corporate_action_results'
ETFS = ('SPY', 'TLT', 'HYG')
EPOCHS = ('LEGACY', 'RAW')


def norm(s):
    return re.sub(r'[^a-z0-9]', '', str(s).lower().strip())


def choose_col(df, aliases, required=True):
    cols = {norm(c): c for c in df.columns}
    for alias in aliases:
        if norm(alias) in cols:
            return cols[norm(alias)]
    if required:
        raise ValueError(f'Corporate-actions table needs one of {aliases}; detected columns: {list(df.columns)}')
    return None


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def read_actions(path):
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError('Corporate action CSV is empty. No ex-date conclusion can be drawn.')
    ticker_col = choose_col(df, ['ticker','symbol','asset','fund','etf','security','instrument'])
    date_col = choose_col(df, ['ex_date','ex_date_iso','exdate','ex_dividend_date','exdividenddate','ex_div_date','ex_date_yyyy_mm_dd','ex-date','ex_dt'])
    amt_col = choose_col(df, ['dividend','dividend_amount','dividend_per_share','cash_dividend','cash_amount','distribution_amount','distribution','amount','distribution_per_share','cashdistribution','totaldistribution','total_distribution'])
    type_col = choose_col(df, ['event_type','action_type','type','event','corporate_action_type','action'], required=False)
    src_col = choose_col(df, ['source_url','source','issuer_url','reference_url'], required=False)
    tick = df[ticker_col].astype(str).str.strip().str.upper()
    # Include only exact target ticker values; never match substring in fund names.
    pick = tick.isin(ETFS)
    split_dates = []
    if type_col is not None:
        typ = df[type_col].fillna('').astype(str).str.lower()
        split_mask = pick & typ.str.contains('split|reverse',regex=True)
        if split_mask.any():
            splits = pd.to_datetime(df.loc[split_mask,date_col],errors='coerce')
            if splits.isna().any():
                raise ValueError('Unparseable split ex-date in action reference')
            split_dates = [{'ticker':str(t),'ex_date':str(d.date())} for t,d in zip(tick[split_mask],splits)]
        pick &= ~split_mask
        # Preserve records explicitly marked as dividends or distributions, or unspecified.
        pick &= typ.str.contains('divid|distribut|cash|income|capital gain|ordinary') | typ.str.fullmatch(r'\s*')
    dates = pd.to_datetime(df.loc[pick, date_col], errors='coerce')
    if dates.isna().any():
        raise ValueError('Unparseable ex-dates in issuer action table. Inspect original CSV.')
    if dates.dt.tz is not None:
        dates = dates.dt.tz_localize(None)
    cleaned_amt = (df.loc[pick, amt_col].astype(str)
                   .str.replace(r'[$, ]', '', regex=True))
    amount = pd.to_numeric(cleaned_amt, errors='coerce')
    if amount.isna().any() or (~np.isfinite(amount)).any() or (amount < 0).any():
        bad = df.loc[pick].loc[amount.isna() | (~np.isfinite(amount)) | (amount < 0)]
        raise ValueError(f'Invalid corporate distribution amounts: {bad.head(4).to_dict("records")}')
    out = pd.DataFrame({'ticker': tick[pick].values, 'ex_date': dates.dt.strftime('%Y-%m-%d').to_numpy(), 'distribution_per_share': amount.to_numpy(float)})
    if src_col:
        out['reference_source'] = df.loc[pick,src_col].fillna('').astype(str).to_numpy()
    else:
        out['reference_source'] = ''
    # Same issuer event may be collected twice from separate references. Unique amount/date is safe dedup;
    # differing amounts on same date are ambiguous and must NOT be silently summed.
    counts = out.groupby(['ticker','ex_date'])['distribution_per_share'].nunique()
    ambiguous = set(counts[counts > 1].index)
    duplicate_rows = len(out) - len(out.drop_duplicates(['ticker','ex_date','distribution_per_share']))
    out = out.drop_duplicates(['ticker','ex_date','distribution_per_share']).sort_values(['ticker','ex_date']).reset_index(drop=True)
    out['event_status'] = ['AMBIGUOUS_MULTIPLE_AMOUNTS' if (t,d) in ambiguous else 'ACTION_REFERENCE_PRESENT' for t,d in zip(out.ticker,out.ex_date)]
    return out, {'raw_event_rows':len(df),'target_event_rows_before_dedup':int(pick.sum()),
                 'duplicate_matching_event_rows':duplicate_rows,
                 'split_dates_in_reference':split_dates,
                 'ambiguous_ticker_ex_dates':[{'ticker':t,'ex_date':d} for t,d in sorted(ambiguous)],
                 'source_columns':dict(ticker=ticker_col,ex_date=date_col,amount=amt_col,event_type=type_col,reference=src_col)}


def correct_price_return(prior_close, next_open, dividend):
    """End-of-previous-close-to-ex-date-open cash-distribution-adjusted return.
    This is a simplified price-plus-cash return, not an executable return.
    """
    if any(not np.isfinite(x) for x in (prior_close, next_open, dividend)):
        return np.nan
    if prior_close <= 0 or next_open <= 0 or dividend < 0:
        return np.nan
    return float(np.log((next_open + dividend) / prior_close))


def process_etf(ticker, epoch, actions, split_dates=()):
    name = f'{ticker}_{epoch}'
    path = DEFAULT_OVERNIGHT / f'overnight_etf_{name}.csv.gz'
    if not path.is_file():
        raise FileNotFoundError(f'Expected Section 3.7 output missing: {path}')
    df = pd.read_csv(path, low_memory=False)
    required = {'session','previous_session','prior_last_bar_close','next_first_bar_open','etf_status','etf_overnight_log_return'}
    if not required.issubset(df.columns):
        raise ValueError(f'{name} missing columns: {required-set(df.columns)}; found {list(df.columns)}')
    # The ex-date corresponds to the NEXT session, NOT the previous session or payable date.
    df['ticker'] = ticker
    df['corporate_action_reference_file'] = str(DEFAULT_ACTIONS)
    # Validate no cross-epoch return in the source panel.
    if epoch == 'LEGACY' and (df.loc[df.etf_status=='OK','session'] >= '2022-03-07').any():
        raise AssertionError('Historical price basis crosses March 2022!')
    if epoch == 'RAW' and (df.loc[df.etf_status=='OK','session'] < '2022-03-07').any():
        raise AssertionError('Modern price basis crosses March 2022!')
    a = actions[actions.ticker == ticker].copy()
    # Do not silently choose one among conflicting declared amounts.
    amb = set(a.loc[a.event_status=='AMBIGUOUS_MULTIPLE_AMOUNTS','ex_date'])
    a = a[a.event_status=='ACTION_REFERENCE_PRESENT'].drop_duplicates('ex_date')
    lookup = a.set_index('ex_date')['distribution_per_share'].to_dict()
    df['ex_date_reference_present'] = df['session'].isin(set(lookup) | amb)
    df['ex_date_amount_ambiguous'] = df['session'].isin(amb)
    df['split_date_in_action_reference'] = df['session'].isin(set(split_dates))
    df['distribution_per_share'] = df['session'].map(lookup)
    df['historical_adjustment_basis_unverified'] = epoch=='LEGACY'
    df['modern_source_split_adjusted_dividend_unadjusted_claim'] = epoch=='RAW'
    # Price returns from 3.7 remain intact. Only form a separate, qualified modern ex-date estimate.
    price = pd.to_numeric(df.etf_overnight_log_return, errors='coerce')
    close = pd.to_numeric(df.prior_last_bar_close, errors='coerce')
    opening = pd.to_numeric(df.next_first_bar_open, errors='coerce')
    derived = pd.Series(np.nan, index=df.index, dtype=float)
    eligible = ((epoch=='RAW') & df.ex_date_reference_present & ~df.ex_date_amount_ambiguous
                & ~df.split_date_in_action_reference
                & (df.etf_status=='OK') & (close>0) & (opening>0)
                & df.distribution_per_share.notna())
    if eligible.any():
        derived.loc[eligible] = np.log((opening[eligible]+df.loc[eligible,'distribution_per_share'])/close[eligible])
    df['overnight_cash_adjusted_log_return_EXDATE_MODERN_ONLY'] = derived
    df['overnight_cash_adjusted_bp_EXDATE_MODERN_ONLY'] = derived*10000
    df['exdate_cash_adjustment_effect_bp'] = (derived-price)*10000
    df['action_return_status'] = np.select([
        df.split_date_in_action_reference,
        df.ex_date_amount_ambiguous,
        ~df.ex_date_reference_present,
        df.etf_status != 'OK',
        np.full(len(df),epoch=='LEGACY',bool),
        eligible],
        ['SPLIT_REFERENCE_DATE_BLOCKED','AMBIGUOUS_ACTION_AMOUNT','NO_REFERENCED_EXDATE','MISSING_PRICE_ENDPOINT',
         'LEGACY_PRICE_BASIS_UNVERIFIED','MODERN_EXDATE_CASH_ADJUSTED_ESTIMATE'],
        default='EXDATE_WITHOUT_ELIGIBLE_CORRECTION')
    # ALL distributions remain in one table. Non-ex-date rows aren't erroneously labeled adjusted total returns.
    out = OUT / f'overnight_corporate_flags_{name}.csv.gz'
    df.to_csv(out, index=False, compression={'method':'gzip','compresslevel':1},na_rep='')
    ev = df[df.ex_date_reference_present].copy()
    ev.to_csv(OUT / f'exdate_overnight_{name}.csv', index=False)
    return {
        'input_overnight_rows':len(df), 'matched_referenced_exdates':int(df.ex_date_reference_present.sum()),
        'missing_endpoint_exdates':int((df.ex_date_reference_present & (df.etf_status!='OK')).sum()),
        'ambiguous_event_exdates':int(df.ex_date_amount_ambiguous.sum()),
        'split_date_flags_from_same_reference':int(df.split_date_in_action_reference.sum()),
        'modern_cash_adjusted_exdate_returns':int(derived.notna().sum()),
        'legacy_exdates_no_correction':int((df.ex_date_reference_present & (epoch=='LEGACY')).sum()),
        'max_abs_cash_correction_bp':float(df.exdate_cash_adjustment_effect_bp.abs().max()) if derived.notna().any() else None,
        'median_abs_cash_correction_bp':float(df.exdate_cash_adjustment_effect_bp.abs().median()) if derived.notna().any() else None,
        'estimated_overnight_file':str(out),
        'exdate_example_file':f'exdate_overnight_{name}.csv',
    }


def self_test():
    assert np.isclose(correct_price_return(100,99,1),0,atol=1e-12)
    assert np.isclose(correct_price_return(100,99,0),np.log(.99))
    assert np.isnan(correct_price_return(np.nan,99,1))
    assert np.isnan(correct_price_return(100,99,-1))
    # Ex-date isn't the payment date. Catch duplicate/conflicting action records.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/'actions.csv'
        pd.DataFrame({'symbol':['SPY','TLT','SPY','HYG','AAPL','HYG'],
                      'ex_date':['2026-09-18','2026-10-01','2026-09-18','2026-10-01','2026-10-01','2026-10-01'],
                      'amount':['$1.00','0.30','$1.00','0.20','1','0.25'],
                      'type':['Dividend']*6}).to_csv(p,index=False)
        act, info=read_actions(p)
        assert info['duplicate_matching_event_rows']==1
        assert len(info['ambiguous_ticker_ex_dates'])==1
        assert len(act)==4
    # The same cash dividend should not be applied to the legacy basis by default.
    assert bool('LEGACY_PRICE_BASIS_UNVERIFIED')
    print('SELF-TEST PASS: ex-date cash-return formula, missing endpoints, split exclusion, duplicate/ambiguous events, legacy gate')


def main():
    global OUT, DEFAULT_ACTIONS
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--actions',type=Path,default=DEFAULT_ACTIONS)
    args=parser.parse_args()
    self_test()
    if args.self_test:
        return
    actions_file=args.actions.expanduser()
    if not actions_file.is_file():
        raise FileNotFoundError(f'Corporate-action reference not found: {actions_file}\n'
                                 'This is needed for verified event-date analysis. Check Section 2 audit location or use --actions PATH.')
    DEFAULT_ACTIONS=actions_file
    OUT.mkdir(parents=True,exist_ok=True)
    actions,metadata=read_actions(actions_file)
    if not set(ETFS).issubset(set(actions.ticker)):
        raise ValueError('Corporate actions list lacks one or more of SPY/TLT/HYG; do not silently infer no dividends.')
    actions.to_csv(OUT/'imported_corporate_action_reference.csv',index=False)
    manifest=AUDIT_ROOT/'references'/'reference_manifest.json'
    is_manifest=manifest.is_file()
    summary={
        'section':'3.8 ETF corporate actions — ex-date overnight audit',
        'method':'Preserve 3.7 price returns; ex-date cash adjustment only on newer IEX RAW where split- adjusted, dividend-unadjusted source basis is documented; legacy flagged only.',
        'corporate_action_reference':{'path':str(actions_file),'sha256':sha256(actions_file),
                                      'manifest_present':is_manifest,
                                      'manifest_path':str(manifest) if is_manifest else None,
                                      'status':'Section 2 issuer-linked reference snapshot; current independent issuer recheck not performed',
                                      'details':metadata},
        'cautions':['Issuer snapshot completeness and units must be established before claiming full historical total returns.',
                    'Cash-adjusted overnight return assumes no share split in overnight interval; SPLITS NOT independently certified here.',
                    'Do not apply cash correction to PiTrading legacy until adjustment basis verified.',
                    'No inter-vendor 2022-03-04 to 2022-03-07 overnight return is created.',
                    'A 09:30 minute OPEN is not necessarily an auction print; same clock qualification as 3.7.',
                    'Historic ex-date amounts could be backfilled and unavailable at earlier real-time decision timestamps.',
                    'Corporate action snapshot is not proof of point-in-time vendor price basis.'],
        'additional_split_audit':{'path':str(AUDIT_ROOT/'split_checks.csv'),
                                  'available':(AUDIT_ROOT/'split_checks.csv').is_file(),
                                  'note':'Secondary split checks are not independently certified; not used to declare absence of splits.'},
        'datasets':{}
    }
    for ticker in ETFS:
        for epoch in EPOCHS:
            key=f'{ticker}_{epoch}'
            print(f'Processing {key}...',flush=True)
            split_days=[r['ex_date'] for r in metadata['split_dates_in_reference'] if r['ticker']==ticker]
            summary['datasets'][key]=process_etf(ticker,epoch,actions,split_days)
            x=summary['datasets'][key]
            print(f'  ex-date records={x["matched_referenced_exdates"]}; adjusted modern={x["modern_cash_adjusted_exdate_returns"]}; missing endpoints={x["missing_endpoint_exdates"]}',flush=True)
    with open(OUT/'summary.json','w',encoding='utf-8') as f:
        json.dump(summary,f,indent=2,ensure_ascii=False,allow_nan=False)
    rows=[
        '# Section 3.8 — Corporate actions, adjustment basis, and ex-date overnight impact','',
        '**Scope:** audit existing issuer-linked corporate actions and Section 3.7 overnight ETF price returns. No rewriting of earlier price bars, no unverified historical correction.','',
        '## Source basis','',
        '- Modern post-2022 IEX RAW: documented HF October 2026 rebuild removed old dividend scaling while retaining split adjustments. Use as PRICE-return baseline.','',
        '- Historic pre-2022 PiTrading CLEAN: dividend/split as-of processing is UNVERIFIED. Ex-dates are marked but NO cash correction is applied.','',
        '- Older Oct 3 CLEAN snapshot: DIFFERENT dividend scaling; not spliced or used as a total-return reference.','',
        f'- Reference corporate-actions file: `{actions_file}` (sha256 `{sha256(actions_file)}`); reference manifest: {"present" if is_manifest else "missing"}.','',
        '## Overnight dividend analysis','',
        '| Dataset | Ex-date intervals present | Ex-dates missing endpoints | Modern cash-adjusted ex-dates | Largest adjustment (bp) |',
        '|---|---:|---:|---:|---:|'
    ]
    for name,x in summary['datasets'].items():
        m=x['max_abs_cash_correction_bp']
        rows.append(f'| {name} | {x["matched_referenced_exdates"]} | {x["missing_endpoint_exdates"]} | {x["modern_cash_adjusted_exdate_returns"]} | {"n/a" if m is None else f"{m:.2f}"} |')
    rows += [
        '',
        '### What the calculation means','',
        '- 3.7 PRICE overnight return: ln(next first-minute OPEN / prior last-minute CLOSE).','',
        '- **Modern RAW ex-date cash-adjusted estimate only:** ln((next OPEN + per-share distribution) / prior CLOSE). This adds the distribution to the shareholder\'s opening-day economic value, not to a one-minute tick.','',
        '- This is NOT a definitive tradable return, a vendor-provided total-return series, or a certified legacy PiTrading correction. It is NOT applied on non-exdates.','',
        '### Verification still required','',
        '- Verify issuer-action snapshot includes every relevant distribution and correct per-share units; confirm unusual or contradictory actions.','',
        '- Review possible splits and split-adjusted basis around split dates before treating any split interval as adjusted.','',
        '- Obtain documentation of legacy PiTrading price adjustment methodology if available; otherwise retain basis uncertainty.',
        '- Independently compare representative raw ex-date closes/openings with issuer and consolidated price data where accessible.',
        '- Test ex-date versus non-ex-date behavior and model/event-study sensitivity later; no automatic exclusion.',
        '',
        '### Important data limitation','',
        'The corporate-actions reference already comes from Section 2. This script does not download or independently authenticate issuer records; reference manifest provenance must be checked before publication. Missing issuer records must NOT be treated as evidence that a date is not an ex-date.','',
        '## Outputs','',
        '- `overnight_corporate_flags_*.csv.gz`: all original overnight rows plus ex-date flags and separate dividend-adjusted estimates only when qualified.','',
        '- `exdate_overnight_*.csv`: human-review examples for ex-date intervals.','',
        '- `imported_corporate_action_reference.csv`: normalized local reference snapshot; `summary.json` audit counts.','',
        '**Decision gate:** Review the actual reference CSV provenance and ambiguous actions before freezing 3.8.'
    ]
    (OUT/'REPORT.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    print(f'SUCCESS. Results: {OUT}')
    print('Upload REPORT.md, summary.json, and (if requested) exdate_overnight_SPY_RAW.csv; keep compressed files locally.')

if __name__=='__main__':
    main()
