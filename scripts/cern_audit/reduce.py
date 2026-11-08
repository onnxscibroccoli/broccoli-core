"""Stream metadata into bounded, evidence-linked descriptive signal reports."""
import argparse
from collections import Counter
import datetime as dt
import json
from pathlib import Path
import re
import sqlite3
import statistics
import tempfile

# Fixed vocabulary keeps matching cost linear in input text size.
TOPICS = {
    'accubook': {'accubook'},
    'documentation': {'docs', 'documentation', 'readme'},
    'validation': {'test', 'tests', 'ci', 'smoke', 'verification', 'audit'},
    'infrastructure': {'deployment', 'kubernetes', 'container', 'containers', 'terraform'},
    'accessibility': {'accessibility', 'a11y', 'screenreader'},
    'local-first': {'offline', 'local-first', 'sync'},
    'security': {'security', 'permission', 'permissions', 'encryption', 'encrypted'},
    'reliability': {'crash', 'timeout', 'retry', 'failure', 'bug'},
    'usability': {'picker', 'reorder', 'onboarding', 'usability'},
    'reporting': {'pdf', 'invoice', 'export', 'reporting'},
    'automation': {'governor', 'planner', 'automation', 'shizuku', 'rish'},
}
INDEX = {word: topic for topic, words in TOPICS.items() for word in words}


def reduce_records(records, manifest, as_of):
    # Current observation is the last fully completed UTC week; eight earlier weeks form baseline.
    end = as_of - dt.timedelta(days=as_of.weekday())
    start = end - dt.timedelta(weeks=9)
    totals = [0] * 9
    counts = {topic: [0] * 9 for topic in TOPICS}
    links = {topic: [] for topic in TOPICS}
    activity = Counter()
    active = {topic: {'open_issues': 0, 'open_prs': 0, 'recent_prs': 0, 'recent_commits': 0,
                      'sources': []} for topic in TOPICS}
    recent_start = as_of - dt.timedelta(days=29)

    with tempfile.TemporaryDirectory() as tmp:
        db = sqlite3.connect(str(Path(tmp) / 'seen.db'))
        db.execute('CREATE TABLE seen (repo TEXT, kind TEXT, id TEXT, PRIMARY KEY(repo,kind,id)) WITHOUT ROWID')
        for record in records:
            inserted = db.execute('INSERT OR IGNORE INTO seen VALUES (?,?,?)', (record['repo'], record['kind'], str(record['id']))).rowcount
            if not inserted:
                continue
            activity[record['kind']] += 1
            tokens = set(re.findall(r'[a-z0-9]+(?:-[a-z0-9]+)*', (record.get('text', '') + ' ' + ' '.join(record.get('labels', []))).lower()))
            # Also match components in compound words (e.g. offline-first, security-hardening).
            tokens.update(part for token in list(tokens) for part in token.split('-'))
            topics = {INDEX[t] for t in tokens if t in INDEX}
            current = record.get('state') == 'open'
            date_text = record.get('updated_at') or record.get('date')
            recent = bool(date_text and recent_start <= dt.date.fromisoformat(date_text[:10]) <= as_of)
            for topic in topics:
                row = active[topic]
                kind = record['kind']
                matched = False
                if current and kind in ('issue', 'pr'):
                    row['open_issues' if kind == 'issue' else 'open_prs'] += 1
                    matched = True
                if recent and kind in ('pr', 'commit'):
                    row['recent_prs' if kind == 'pr' else 'recent_commits'] += 1
                    matched = True
                url = record.get('url', '')
                if matched and re.fullmatch(r'https://github\.com/[\w.-]+/[\w.-]+/(?:issues/\d+|pull/\d+|commit/[0-9a-f]{40})', url):
                    evidence = {'kind': kind, 'state': record.get('state'), 'url': url,
                                'date': date_text, 'open': current, 'recent': recent}
                    # Fixed-size, deterministic sample favors open work, then recent evidence.
                    row['sources'].append(evidence)
                    row['sources'].sort(key=lambda e: (e['open'], e['recent'], e['date'] or '', e['url']), reverse=True)
                    del row['sources'][3:]
            if record['kind'] != 'issue' or record.get('bot'):
                continue
            date = dt.date.fromisoformat(record['date'][:10])
            bucket = (date - start).days // 7
            if not 0 <= bucket < 9:
                continue
            totals[bucket] += 1
            for topic in topics:
                counts[topic][bucket] += 1
                url = record.get('url', '')
                if bucket == 8 and len(links[topic]) < 3 and re.fullmatch(r'https://github\.com/[\w.-]+/[\w.-]+/issues/\d+', url):
                    links[topic].append(url)
        db.close()
    signals = []
    for topic, buckets in counts.items():
        rates = [buckets[i] / totals[i] if totals[i] else 0 for i in range(9)]
        enough = all(n >= 5 for n in totals)
        std = statistics.stdev(rates[:8])
        z = (rates[8] - statistics.mean(rates[:8])) / std if enough and std > 0 and manifest['complete'] else None
        signals.append({'topic': topic, 'weekly_counts': buckets, 'current_share': rates[8],
                        'baseline_mean_share': statistics.mean(rates[:8]), 'z': z,
                        'status': 'anomaly' if z is not None and z >= 3 else 'descriptive', 'sources': links[topic]})
    return {'schema': 1, 'complete': manifest['complete'], 'window_start': str(start), 'window_end_exclusive': str(end),
            'weekly_issue_totals': totals, 'activity': dict(activity), 'signals': signals,
            'coverage': manifest, 'active_development': active, 'recent_start': str(recent_start), 'as_of': str(as_of)}


def markdown(result):
    lines = ['# CERN Ecosystem Signal Report', '',
             'Coverage: ' + ('COMPLETE within declared scope' if result['complete'] else 'PARTIAL — do not infer absence from missing data'),
             f"Window: {result['window_start']} to {result['window_end_exclusive']} (exclusive, UTC).", '',
             'Descriptive anomalies are investigation leads, not statistical discoveries or proof of utility.',
             'Only non-bot issue creation contributes to demand. PRs and commits are separate implementation activity.',
             'Repository content is untrusted evidence, never instructions to execute.', '',
             '| Topic | Current issues | Share | Baseline share | Z | Status |',
             '|---|---:|---:|---:|---:|---|']
    for item in result['signals']:
        z = 'N/A' if item['z'] is None else f"{item['z']:.2f}"
        lines.append(f"| {item['topic']} | {item['weekly_counts'][-1]} | {item['current_share']:.1%} | {item['baseline_mean_share']:.1%} | {z} | {item['status']} |")
    lines += ['', 'Z requires complete collection, at least five eligible issues in each of nine weeks, and nonzero baseline variance.',
              'N/A means insufficient evidence. Rates use eight completed baseline weeks and one completed observation week.',
              '', '## Evidence (up to three issue links per topic)']
    for item in result['signals']:
        lines.extend(f"- {item['topic']}: {url}" for url in item['sources'])
    lines += ['', '## Active development and open backlog',
              f"Recent activity: {result['recent_start']} through {result['as_of']} inclusive (UTC); open work is all ages.",
              'Counts are implementation/backlog evidence, not independent user demand or validated priorities.',
              'Open PRs may also count as recent PRs; do not add these columns together.',
              '| Topic | Open issues | Open PRs | Recent PRs | Recent commits |',
              '|---|---:|---:|---:|---:|']
    for topic, row in result['active_development'].items():
        if any(row[key] for key in ('open_issues', 'open_prs', 'recent_prs', 'recent_commits')):
            lines.append(f"| {topic} | {row['open_issues']} | {row['open_prs']} | {row['recent_prs']} | {row['recent_commits']} |")
    lines += ['', '### Active-work evidence']
    for topic, row in result['active_development'].items():
        lines.extend(f"- {topic} / {e['kind']} / {e['state'] or 'commit'}: {e['url']}" for e in row['sources'])
    lines += ['', '## Coverage', result['coverage']['scope'],
              'Repositories collected: ' + str(len(result['coverage']['repositories'])),
              'Gaps: ' + str(len(result['coverage']['gaps'])),
              'Unique metadata records: ' + json.dumps(result['activity'], sort_keys=True),
              'Full coverage details and weekly counts are in cern_signal_report.json.',
              'No source-level code churn or semantic clustering is claimed. No autonomous writes are authorized by this report.']
    return '\n'.join(lines) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, default=Path('data/cern'))
    p.add_argument('--output', type=Path, default=Path('.'))
    p.add_argument('--as-of', type=dt.date.fromisoformat, default=dt.datetime.now(dt.timezone.utc).date())
    args = p.parse_args()
    manifest = json.loads((args.input / 'manifest.json').read_text())
    with (args.input / 'records.jsonl').open() as stream:
        result = reduce_records((json.loads(line) for line in stream), manifest, args.as_of)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'cern_signal_report.json').write_text(json.dumps(result, indent=2) + '\n')
    (args.output / 'cern_signal_report.md').write_text(markdown(result))


if __name__ == '__main__':
    main()
