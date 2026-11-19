#!/usr/bin/env python3
"""Section 3.2: timestamp semantics and clock alignment. Read-only.

Uses the frozen Section 2 input files. It does NOT clean bars, calculate returns,
choose HMM settings, or claim to identify undocumented legacy candle boundaries.

Requirements: python -m pip install pandas numpy pandas_market_calendars
(Alternatively exchange_calendars works.)

Run: python "%USERPROFILE%\\Downloads\\section3_2_timestamp_alignment.py"
Output: ~/Downloads/section3_2_timestamp_results/{REPORT.md,summary.json,dst_examples.csv}
"""
from __future__ import annotations

import json
import sys
import zipfile
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HOME = Path.home()
RAW = HOME / 'OneDrive' / 'Desktop' / 'data' / 'raw'
DL = HOME / 'Downloads'
OUT = DL / 'section3_2_timestamp_results'
ET = 'America/New_York'
START = '2002-12-30'
END = '2026-10-14'
CHUNK = 450_000
MIN_NS = 60_000_000_000

DATASETS = {
    'SPY_LEGACY': {'path': RAW / 'SPY_clean_1min.csv', 'symbol': 'SPY', 'kind': 'legacy', 'tag': 'pitrading'},
    'TLT_LEGACY': {'path': RAW / 'TLT_clean_1min.csv', 'symbol': 'TLT', 'kind': 'legacy', 'tag': 'pitrading'},
    'HYG_LEGACY': {'path': RAW / 'HYG_clean_1min.csv', 'symbol': 'HYG', 'kind': 'legacy', 'tag': 'pitrading'},
    'SPY_RAW': {'path': DL / 'hfdatalibrary_raw_1min_1tickers_2026-10-13.zip', 'symbol': 'SPY', 'kind': 'modern'},
    'TLT_RAW': {'path': DL / 'hfdatalibrary_raw_1min_2tickers_2026-10-15.zip', 'fallback': RAW / 'hf_raw' / 'TLT_raw_1min.csv', 'symbol': 'TLT', 'kind': 'modern'},
    'HYG_RAW': {'path': DL / 'hfdatalibrary_raw_1min_2tickers_2026-10-15.zip', 'fallback': RAW / 'hf_raw' / 'HYG_raw_1min.csv', 'symbol': 'HYG', 'kind': 'modern'},
    'GOLD_BID': {'path': RAW / 'xauusd-m1-bid-2007-04-11-2026-10-02 - Copy.csv', 'kind': 'quote'},
    'GOLD_ASK': {'path': RAW / 'xauusd-m1-ask-2007-04-11-2026-10-02.csv', 'kind': 'quote'},
    'DOLLAR_BID': {'path': RAW / 'dollaridxusd-m1-bid-2017-12-01-2026-10-02.csv', 'kind': 'quote'},
    'DOLLAR_ASK': {'path': RAW / 'dollaridxusd-m1-ask-2017-12-01-2026-10-02.csv', 'kind': 'quote'},
}

# Docs are guidance only, not proof about undocumented historical CSVs.
REFERENCES = {
    'hf_session': 'https://hfdatalibrary.com/pages/issues',
    'hf_fields': 'https://hfdatalibrary.com/pages/dictionary',
    'hf_sources': 'https://hfdatalibrary.com/pages/docs',
    'dukascopy_node_cli': 'https://github.com/Leo4815162342/dukascopy-node/blob/master/src/cli/config.ts',
}


def build_xnys_grid():
    """All scheduled RTH minute START instants as UTC int64 ns, early closes included."""
    try:
        import pandas_market_calendars as pmc
        sch = pmc.get_calendar('XNYS').schedule(start_date=START, end_date=END)
        opens = pd.to_datetime(sch['market_open'], utc=True)
        closes = pd.to_datetime(sch['market_close'], utc=True)
        lib = 'pandas_market_calendars'
    except ImportError:
        try:
            import exchange_calendars as ec
            sch = ec.get_calendar('XNYS', start=START, end=END).schedule
            opens = pd.to_datetime(sch['open'], utc=True)
            closes = pd.to_datetime(sch['close'], utc=True)
            lib = 'exchange_calendars'
        except ImportError:
            raise RuntimeError('Install a calendar: python -m pip install pandas_market_calendars')
    starts = opens.astype('int64').to_numpy()
    ends = closes.astype('int64').to_numpy()
    all_minutes = np.concatenate([np.arange(a, b, MIN_NS, dtype=np.int64)
                                  for a, b in zip(starts, ends) if b > a])
    if all_minutes.size < 2_000_000:
        raise RuntimeError('NYSE calendar produced too few minutes; refusing invalid audit.')
    print(f'NYSE calendar: {len(opens):,} sessions, {all_minutes.size:,} minute starts ({lib})', flush=True)
    return all_minutes, sch, lib


@contextmanager
def open_dataset(spec):
    path = spec['path']
    if not path.exists() and spec.get('fallback') and spec['fallback'].exists():
        path = spec['fallback']
    if not path.exists():
        raise FileNotFoundError(str(path))
    if path.suffix.lower() != '.zip':
        with path.open('rb') as fh:
            yield fh, str(path), None
    else:
        with zipfile.ZipFile(path) as zf:
            member = next((x for x in zf.namelist()
                           if x.lower().endswith(f"{spec['symbol'].lower()}_raw_1min.csv")), None)
            if member is None:
                raise FileNotFoundError(f'{spec["symbol"]}_raw_1min.csv not found in {path}')
            with zf.open(member) as fh:
                yield fh, str(path), member


def identify_time_column(columns):
    by_lower = {str(c).strip().lower(): c for c in columns}
    for key in ('datetime', 'timestamp', 'time', 'date', 'gmt time', 'local time', 'date_time'):
        if key in by_lower:
            return by_lower[key]
    raise ValueError(f'No recognizable datetime column: {list(columns)}')


def parse_time(s, kind):
    s = s.astype('string').str.strip()
    nonempty = s.dropna()
    if len(nonempty) == 0:
        raise ValueError('Timestamp column is empty.')
    probe = nonempty.iloc[0]
    if probe.replace('.', '', 1).isdigit():
        # Dukascopy-node exports typically use Unix milliseconds.
        length = len(probe.split('.')[0].lstrip('+-'))
        unit = 'ns' if length >= 18 else 'us' if length >= 15 else 'ms' if length >= 12 else 's' if length >= 10 else None
        if unit is None:
            raise ValueError(f'Numeric timestamps have unsupported epoch width: {probe}')
        parsed = pd.to_datetime(pd.to_numeric(s, errors='coerce'), unit=unit, utc=True, errors='coerce')
        return parsed, 'epoch_' + unit
    if kind == 'quote':
        # Dukascopy download command specified -utc 0. Unmarked strings are UTC.
        parsed = pd.to_datetime(s, utc=True, errors='coerce', format='mixed')
        return parsed, 'utc_text_assumed_from_export_settings'
    parsed = pd.to_datetime(s, errors='coerce', format='mixed')
    if getattr(parsed.dt, 'tz', None) is not None:
        raise ValueError('ETF timestamp has an embedded timezone; requires explicit review.')
    return parsed, 'naive_text'


def to_ns(idx):
    return idx.astype('int64').to_numpy(dtype=np.int64)


def native_et_to_utc_ns(naive):
    local = naive.dt.tz_localize(ET, ambiguous='NaT', nonexistent='NaT')
    return local.dt.tz_convert('UTC').astype('int64').to_numpy(dtype=np.int64)


def read_times(name, spec, valid_rth):
    print(f'Reading {name} ...', flush=True)
    chunks = []
    rows = 0
    bad = 0
    fmt = None
    with open_dataset(spec) as (fh, pathname, member):
        header = pd.read_csv(fh, nrows=0)
        tcol = identify_time_column(header.columns)
        usecols = [tcol]
        if spec.get('tag'):
            lower = {str(c).lower(): c for c in header.columns}
            if 'source' not in lower:
                raise ValueError(f'{name}: source column missing; cannot isolate historical records')
            scol = lower['source']
            usecols.append(scol)
        fh.seek(0)
        for frame in pd.read_csv(fh, usecols=usecols, chunksize=CHUNK, dtype='string'):
            if spec.get('tag'):
                frame = frame.loc[frame[scol].str.lower().eq(spec['tag'])]
            if frame.empty:
                continue
            times, fmt = parse_time(frame[tcol], spec['kind'])
            invalid = times.isna()
            bad += int(invalid.sum())
            times = times.loc[~invalid]
            rows += len(times)
            if spec['kind'] == 'quote':
                values = to_ns(times)
                values = values[np.isin(values, valid_rth, assume_unique=False)]
            else:
                # ETF native datetimes are retained to compare two timezone hypotheses.
                values = to_ns(times)
            chunks.append(values)
    if rows == 0:
        raise ValueError(f'{name}: zero valid timestamp rows found')
    values = np.unique(np.concatenate(chunks)) if chunks else np.array([], dtype='int64')
    return values, {'path': pathname, 'zip_member': member, 'rows': int(rows),
                    'unique_loaded': int(values.size),
                    'invalid_timestamps': bad, 'source_time_format': fmt,
                    'time_column': str(tcol),
                    'note': 'quotes retain RTH minute timestamps only' if spec['kind'] == 'quote' else 'ETF retains all source timestamps'}


def candidate_score(values, expected):
    if len(values) == 0:
        return {'on_exchange_grid': 0, 'share_of_observed_on_grid_pct': None}
    good = int(np.isin(values, expected).sum())
    return {'on_exchange_grid': good, 'share_of_observed_on_grid_pct': round(good * 100 / len(values), 4)}


def etf_edge_counts(et_utc_values):
    et = pd.to_datetime(et_utc_values, utc=True).tz_convert(ET)
    h = et.hour.to_numpy()
    m = et.minute.to_numpy()
    d = et.date
    early = ((h == 9) & (m == 30))
    end = ((h == 15) & (m == 59))
    at1600 = ((h == 16) & (m == 0))
    at0931 = ((h == 9) & (m == 31))
    dates = np.unique(np.asarray(d, dtype='datetime64[D]'))
    return {
        'unique_record_dates': len(dates),
        'session_dates_with_0930_label': int(np.unique(np.asarray(d, dtype='datetime64[D]')[early]).size),
        'session_dates_with_0931_label': int(np.unique(np.asarray(d, dtype='datetime64[D]')[at0931]).size),
        'session_dates_with_1559_label': int(np.unique(np.asarray(d, dtype='datetime64[D]')[end]).size),
        'session_dates_with_1600_label': int(np.unique(np.asarray(d, dtype='datetime64[D]')[at1600]).size),
    }


def dst_rows(expected, arrays):
    # Dates before and after US daylight-saving switch and a control day.
    special = ('2024-03-08', '2024-03-11', '2024-11-01', '2024-11-04', '2020-03-09')
    samples = []
    for day in special:
        start_local = pd.Timestamp(f'{day} 09:30:00', tz=ET)
        start_utc = int(start_local.tz_convert('UTC').value)
        for minute in (0, 1, 2, 3, 5, 10, 30):
            when = start_utc + minute * MIN_NS
            record = {'session_date': day,
                      'new_york_label': str(pd.Timestamp(when, unit='ns', tz='UTC').tz_convert(ET)),
                      'utc_label': str(pd.Timestamp(when, unit='ns', tz='UTC')),
                      'earliest_complete_bar_utc_if_start_labeled': str(pd.Timestamp(when + MIN_NS, unit='ns', tz='UTC')),
                      'scheduled_rth_minute': bool(np.isin(when, expected))}
            for name, arr in arrays.items():
                record[name] = int(np.isin(when, arr))
            samples.append(record)
    return pd.DataFrame(samples)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    grid, calendar, lib = build_xnys_grid()
    raw, meta, errors = {}, {}, {}
    for name, spec in DATASETS.items():
        try:
            raw[name], meta[name] = read_times(name, spec, grid)
            print(f'  {name}: {meta[name]["rows"]:,} time labels read', flush=True)
        except Exception as exc:
            errors[name] = f'{type(exc).__name__}: {exc}'
            print(f'  NOT LOADED {name}: {errors[name]}', flush=True)
    etfs = {}
    arrays = {}
    for name, spec in DATASETS.items():
        if name not in raw or spec['kind'] == 'quote':
            continue
        naive = pd.Series(pd.to_datetime(raw[name], unit='ns'))
        et_values = native_et_to_utc_ns(naive)
        et_values = et_values[et_values != np.iinfo('int64').min]
        et_values = np.unique(et_values)
        arrays[name] = et_values
        et_sc = candidate_score(et_values, grid)
        alt_sc = candidate_score(raw[name], grid)  # naive labels interpreted UTC
        etfs[name] = {
            'interpret_native_as_new_york': et_sc,
            'interpret_native_as_utc': alt_sc,
            'boundary_label_evidence_under_new_york': etf_edge_counts(et_values),
            'source': spec['kind'],
            'current_timing_assumption': 'Eastern clock labels, start of minute (not a certified legacy fact)' if spec['kind']=='legacy' else 'Eastern clock labels, start of minute (HF IEX docs)',
        }
    pairs = {}
    for prefix in ('GOLD', 'DOLLAR'):
        a, b = prefix + '_BID', prefix + '_ASK'
        if a in raw and b in raw:
            pair = np.intersect1d(raw[a], raw[b], assume_unique=True)
            arrays[prefix + '_PAIRED'] = pair
            pairs[prefix] = {
                'bid_rth_labels': len(raw[a]), 'ask_rth_labels': len(raw[b]),
                'paired_rth_labels': len(pair),
                'all_grid_minutes_not_a_coverage_denominator': len(grid),
                'paired_date_span': [str(pd.Timestamp(pair[0], unit='ns', tz='UTC')), str(pd.Timestamp(pair[-1], unit='ns', tz='UTC'))] if len(pair) else None,
                'time_convention': 'UTC minute-start supported by original -utc 0 download and exporter, not quote freshness',
            }
    overlap = {}
    for source in ('SPY_LEGACY', 'SPY_RAW'):
        if source not in arrays:
            continue
        for target in ('TLT_LEGACY', 'HYG_LEGACY', 'TLT_RAW', 'HYG_RAW', 'GOLD_PAIRED', 'DOLLAR_PAIRED'):
            if target not in arrays:
                continue
            if source.endswith('LEGACY') and target.endswith('RAW'):
                continue
            if source.endswith('RAW') and target.endswith('LEGACY'):
                continue
            common = np.intersect1d(arrays[source], arrays[target], assume_unique=True)
            overlap[f'{source}--{target}'] = {'same_label_minutes': int(len(common)),
                'warning': 'Equality of labels does NOT verify underlying candle start/end convention or stale-quote freedom'}
    dst = dst_rows(grid, arrays)
    dst_path = OUT / 'dst_examples.csv'
    dst.to_csv(dst_path, index=False)
    output = {
        'scope': 'Section 3.2 timestamps and synchronization: NO model, NO cleaning',
        'calendar_library': lib,
        'calendar_minutes': len(grid),
        'documentation': REFERENCES,
        'etf_checks': etfs,
        'dukascopy_checks': pairs,
        'paired_label_counts': overlap,
        'files': meta,
        'load_errors': errors,
        'limitations': [
            'Time-of-day and session fit are strong clues about timezone, not proof of legacy provider timezone or bar interval boundary.',
            'A price labelled 09:30 from a start-labelled 1m bar is not fully known until 09:31 (at earliest).',
            'Quote labels and exact bid/ask pairing do not establish actual bid/ask tick freshness.',
            'Neither label overlaps nor correlations prove true causality or bar semantics.',
            'External independent timestamped trade or provider specification is required to certify undocumented historical bar boundaries.',
            'Rows were read, never altered. Early-close minutes use an exchange calendar.',
        ],
    }
    (OUT/'summary.json').write_text(json.dumps(output, indent=2, default=str), encoding='utf-8')
    lines = [
        '# Section 3.2 — Timestamp and synchronization audit', '',
        '**Read-only. This does not clean the data or decide missingness rules.**', '',
        '## Reference interpretation',
        '- Modern HF/IEX trades start no earlier than 09:30 and finish before 16:00 ET, with labels 09:30–15:59: **start-label convention is strongly documented**.',
        '- Legacy pre-2022 native timezone and exact bar labeling were not certified by the original data vendor.',
        '- Dukascopy downloads used UTC 0; minute-start labels supported by exporter provenance.',
        '- Treat completed start-labeled 09:30 bar as available **no earlier than 09:31**.', '',
        '## File status',
    ]
    for name in DATASETS:
        if name in meta:
            lines.append(f'- **{name}:** loaded {meta[name]["rows"]:,} timestamps; source `{meta[name]["path"]}`')
        else:
            lines.append(f'- **{name}: ERROR** {errors.get(name,"Unknown")}. This part is UNRESOLVED.')
    lines += ['', '## ETF timing evidence (native labels)', '']
    for name, v in etfs.items():
        ed = v['interpret_native_as_new_york']['share_of_observed_on_grid_pct']
        ud = v['interpret_native_as_utc']['share_of_observed_on_grid_pct']
        edges = v['boundary_label_evidence_under_new_york']
        lines += [f'### {name}',
                  f'- If interpreted as New York clock: **{ed}%** of labels fit actual NYSE scheduled minute starts.',
                  f'- If interpreted as UTC: **{ud}%** fit the same schedule.',
                  f'- Days containing 09:30 / 09:31 / 15:59 / 16:00 labels: **{edges["session_dates_with_0930_label"]} / {edges["session_dates_with_0931_label"]} / {edges["session_dates_with_1559_label"]} / {edges["session_dates_with_1600_label"]}**.',
                  '- Interpretation: these counts support or challenge a clock hypothesis; cannot certify undocumented legacy start/end rules.', '']
    lines += ['## Gold and dollar pairing (only exchange-session labels)', '']
    for name, v in pairs.items():
        lines.append(f'- **{name}:** {v["paired_rth_labels"]:,} exact paired UTC minute labels during NYSE trading hours (bid {v["bid_rth_labels"]:,}; ask {v["ask_rth_labels"]:,}).')
    lines += ['', '## Same-label intersections (not causal synchronization proof)', '']
    for k, v in overlap.items():
        lines.append(f'- {k}: {v["same_label_minutes"]:,} labels.')
    lines += ['', '## DST and information availability',
              '- `dst_examples.csv` shows representative US DST-transition sessions, ETF/quote presence and the earliest end of a start-labeled candle.',
              '- A matching 09:30 label means aligned *labels*, not that the final 09:30 candle values can be used at 09:30.', '',
              '## What remains to decide before freezing 3.2',
              '- Preserve an explicit **historical label-boundary uncertainty**; if it cannot be verified with source-level evidence, use a 1-minute timing sensitivity scenario.',
              '- Ensure all reported model features use data available at their computed `bar_end` time, not at the start label.',
              '- Never claim label matching alone proves minute-level economic leadership.',
              '- Data cleaning, return construction and HMM robustness belong to later subsections.', '',
              '## Online references',
             ]
    lines += [f'- {k}: {v}' for k, v in REFERENCES.items()]
    if errors:
        lines += ['', '**INCOMPLETE:** At least one source failed to load. Fix the listed file paths; do not freeze this audit yet.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print('\nCOMPLETE' if not errors else '\nPARTIAL (errors listed)', flush=True)
    print(f'Results: {OUT}', flush=True)
    print('Please upload REPORT.md and summary.json.', flush=True)
    return 0 if not errors else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'FATAL: {type(exc).__name__}: {exc}', file=sys.stderr)
        raise
