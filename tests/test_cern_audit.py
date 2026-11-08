import datetime as dt
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
from scripts.cern_audit.harvest import API, harvest
from scripts.cern_audit.reduce import reduce_records, markdown


class AuditTests(unittest.TestCase):
    def manifest(self, complete=True):
        return {'complete': complete, 'scope': 'test', 'repositories': ['o/r'], 'gaps': []}

    def records(self):
        start = dt.date(2026, 8, 31)
        for week in range(9):
            for i in range(10):
                yield {'repo': 'o/r', 'kind': 'issue', 'id': week * 10 + i,
                       'text': 'security' if i < (week % 2 + 1 if week < 8 else 9) else 'unmatched',
                       'date': str(start + dt.timedelta(weeks=week)),
                       'url': f'https://github.com/o/r/issues/{week * 10 + i + 1}'}

    def test_anomaly_and_duplicate_suppression(self):
        rows = list(self.records())
        result = reduce_records(iter(rows + rows), self.manifest(), dt.date(2026, 11, 2))
        self.assertEqual(result['activity']['issue'], 90)
        self.assertEqual(result['weekly_issue_totals'], [10] * 9)
        security = next(x for x in result['signals'] if x['topic'] == 'security')
        self.assertGreater(security['z'], 5)
        self.assertEqual(security['status'], 'anomaly')
        self.assertEqual(len(security['sources']), 3)
        self.assertLess(len(markdown(result)), 12000)

    def test_partial_and_zero_variance_never_significant(self):
        partial = reduce_records(self.records(), self.manifest(False), dt.date(2026, 11, 2))
        self.assertTrue(all(x['z'] is None for x in partial['signals']))
        empty = reduce_records(iter([]), self.manifest(), dt.date(2026, 11, 2))
        self.assertTrue(all(x['z'] is None for x in empty['signals']))
        self.assertIn('N/A', markdown(empty))

    def test_bots_prs_current_week_excluded(self):
        rows = list(self.records())
        for row in rows:
            row['bot'] = True
        rows += [{'repo': 'o/r', 'kind': 'pr', 'id': 1000},
                 {'repo': 'o/r', 'kind': 'issue', 'id': 1001, 'date': '2026-11-02', 'text': 'security'}]
        result = reduce_records(iter(rows), self.manifest(), dt.date(2026, 11, 2))
        self.assertEqual(sum(result['weekly_issue_totals']), 0)

    def test_pagination_and_budget(self):
        api = API('unused', 0)
        with self.assertRaises(RuntimeError):
            api.get('repos/o/r')
        with patch.object(api, 'get', side_effect=[[{}] * 100, [{}]]) as get:
            self.assertEqual(len(list(api.pages('repos/o/r/issues?state=all'))), 101)
            self.assertIn('&per_page=100&page=2', get.call_args.args[0])

    def test_transient_retry_and_permission_failure(self):
        api = API('unused')
        error = urllib.error.HTTPError('url', 503, 'busy', {}, None)
        with patch('urllib.request.urlopen', side_effect=[error, io.BytesIO(b'[]')]), patch('time.sleep') as sleep:
            self.assertEqual(api.get('repos/o/r/branches'), [])
            sleep.assert_called_once()
        denied = urllib.error.HTTPError('url', 403, 'denied', {}, None)
        with patch('urllib.request.urlopen', side_effect=denied), patch('time.sleep') as sleep:
            with self.assertRaises(RuntimeError):
                api.get('repos/o/r/branches')
            sleep.assert_not_called()

    def test_single_repository_pilot(self):
        class Fake:
            requests = 3
            def get(self, path):
                self.path = path
                return {'owner': {'login': 'o'}, 'fork': False, 'private': False, 'full_name': 'o/r'}
            def pages(self, path):
                return iter([])
        api = Fake()
        with tempfile.TemporaryDirectory() as tmp:
            result = harvest(api, 'o', Path(tmp), repository='o/r')
            self.assertTrue(result['complete'])
            self.assertEqual(result['repositories'], ['o/r'])
            self.assertEqual(api.path, 'repos/o/r')

    def test_harvest_failure_records_gap_and_private_exclusion(self):
        class Fake:
            requests = 3
            def pages(self, path):
                if path.startswith('users/'):
                    return iter([{'owner': {'login': 'o'}, 'fork': False, 'private': False, 'full_name': 'o/r'},
                                 {'owner': {'login': 'o'}, 'fork': False, 'private': True, 'full_name': 'o/private'}])
                raise RuntimeError('denied')
        with tempfile.TemporaryDirectory() as tmp:
            result = harvest(Fake(), 'o', Path(tmp))
            self.assertFalse(result['complete'])
            self.assertEqual(result['repositories'], ['o/r'])
            self.assertEqual(len(result['gaps']), 2)
            self.assertEqual(json.loads((Path(tmp) / 'manifest.json').read_text()), result)


if __name__ == '__main__':
    unittest.main()
