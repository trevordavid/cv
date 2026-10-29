import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ads.search import Article
import requests

import update_metrics as metrics


def paper(citations, bibcode="paper"):
    return Article(
        id=bibcode, bibcode=bibcode, citation_count=citations,
        read_count=2, downloads=None,
    )


def response(docs=(), total=None, status=200, cursor="next", rows=2000):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps({
        "responseHeader": {"params": {
            "rows": str(rows),
            "fl": "id,bibcode,citation_count,read_count,downloads",
        }},
        "response": {
            "numFound": len(docs) if total is None else total,
            "docs": [{"id": str(i), "bibcode": code, "citation_count": count}
                     for i, (code, count) in enumerate(docs)],
        },
        "nextCursorMark": cursor,
    }).encode()
    return result


class MetricsTests(unittest.TestCase):
    def test_indices_and_missing_counts(self):
        result = metrics.calculate_metrics([paper(c) for c in [10, 8, 5, 3, 0, None]])
        self.assertEqual(result, {
            "total_papers": 6, "total_citations": 26, "total_reads": 12,
            "total_downloads": 0, "h_index": 3, "g_index": 5, "i10_index": 1,
        })

    def test_invalid_counts_are_rejected(self):
        for value in (-1, 1.5, True, "NaN", "bad"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                metrics.calculate_metrics([paper(value)])

    @patch("requests.adapters.HTTPAdapter.send")
    def test_fetch_uses_timeout_and_token(self, send):
        send.return_value = response([("a", 4)])
        publications = metrics.fetch_publications("library", "test-token")
        self.assertEqual(publications[0].citation_count, 4)
        self.assertEqual(send.call_args.kwargs["timeout"], (10, 30))
        self.assertEqual(send.call_args.args[0].headers["Authorization"], "Bearer test-token")

    @patch("requests.adapters.HTTPAdapter.send")
    def test_fetch_reads_all_pages_when_ads_caps_page_size(self, send):
        send.side_effect = [
            response([("a", 4)], total=2, rows=1, cursor="second"),
            response([("b", 3)], total=2, rows=1, cursor="done"),
        ]
        with self.assertWarns(UserWarning):
            publications = metrics.fetch_publications("library", "token")
        self.assertEqual([pub.bibcode for pub in publications], ["a", "b"])
        self.assertEqual(send.call_count, 2)

    @patch("update_metrics.time.sleep")
    @patch("requests.adapters.HTTPAdapter.send")
    def test_transient_failure_retries_with_backoff(self, send, sleep):
        send.side_effect = [
            response(status=503), requests.exceptions.Timeout(),
            response([("a", 4)]),
        ]
        self.assertEqual(len(metrics.fetch_publications("library", "token")), 1)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [5, 10])

    @patch("update_metrics.time.sleep")
    @patch("requests.adapters.HTTPAdapter.send")
    def test_retry_exhaustion_is_fatal(self, send, sleep):
        send.return_value = response(status=429)
        with self.assertRaises(requests.exceptions.HTTPError):
            metrics.fetch_publications("library", "token", attempts=3)
        self.assertEqual(send.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    @patch("update_metrics.time.sleep")
    @patch("requests.adapters.HTTPAdapter.send")
    def test_authentication_errors_are_not_retried(self, send, sleep):
        for status in (400, 401, 403, 404):
            with self.subTest(status=status):
                send.reset_mock()
                send.return_value = response(status=status)
                with self.assertRaises(requests.exceptions.HTTPError):
                    metrics.fetch_publications("library", "token")
                send.assert_called_once()
        sleep.assert_not_called()

    @patch("requests.adapters.HTTPAdapter.send")
    def test_empty_and_duplicate_libraries_are_rejected(self, send):
        for docs in ([], [("a", 2), ("a", 3)], [("", 3)]):
            with self.subTest(docs=docs):
                send.return_value = response(docs)
                with self.assertRaises(ValueError):
                    metrics.fetch_publications("library", "token")

    @patch("update_metrics.ads.SearchQuery")
    def test_truncated_result_is_rejected(self, query_type):
        query = query_type.return_value
        query.__iter__.return_value = iter([paper(3)])
        query.response.numFound = 2
        with self.assertRaisesRegex(ValueError, "incomplete"):
            metrics.fetch_publications("library", "token")


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.destination = Path(self.temp.name) / "metrics.tex"
        self.destination.write_text("last known good metrics", encoding="utf-8")

    @patch("update_metrics.fetch_publications")
    def test_second_library_failure_preserves_existing_file(self, fetch):
        fetch.side_effect = [[paper(10)], requests.exceptions.Timeout()]
        with self.assertRaises(requests.exceptions.Timeout):
            metrics.update_metrics("token", self.destination)
        self.assertEqual(self.destination.read_text(), "last known good metrics")
        self.assertEqual(list(Path(self.temp.name).iterdir()), [self.destination])

    @patch("update_metrics.fetch_publications")
    def test_invalid_lead_totals_preserve_existing_file(self, fetch):
        fetch.side_effect = [[paper(5)], [paper(10)]]
        with self.assertRaisesRegex(ValueError, "exceed"):
            metrics.update_metrics("token", self.destination)
        self.assertEqual(self.destination.read_text(), "last known good metrics")

    @patch("update_metrics.fetch_publications")
    def test_successful_update_is_idempotent(self, fetch):
        fetch.side_effect = [
            [paper(10), paper(3)], [paper(3)],
            [paper(10), paper(3)], [paper(3)],
        ]
        metrics.update_metrics("token", self.destination)
        self.assertEqual(self.destination.read_text(), (
            "1 lead author papers (3 citations),\n"
            "2 total papers (13 citations).\\newline\n"
            "h-index: 2, g-index: 2, i10-index: 1. Updated \\today.\n"
        ))
        modified = self.destination.stat().st_mtime_ns
        metrics.update_metrics("token", self.destination)
        self.assertEqual(self.destination.stat().st_mtime_ns, modified)

    @patch("update_metrics.fetch_publications", return_value=[paper(3)])
    def test_replace_failure_preserves_previous_file_and_cleans_temp(self, fetch):
        with patch.object(Path, "replace", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                metrics.update_metrics("token", self.destination)
        self.assertEqual(self.destination.read_text(), "last known good metrics")
        self.assertEqual(list(Path(self.temp.name).iterdir()), [self.destination])

    @patch("update_metrics.fetch_publications")
    def test_invalid_settings_fail_before_network(self, fetch):
        for kwargs in (
            {"token": ""}, {"token": "token", "attempts": 0},
            {"token": "token", "base_delay": float("nan")},
            {"token": "token", "base_delay": -1},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                metrics.update_metrics(destination=self.destination, **kwargs)
        fetch.assert_not_called()

    @patch("update_metrics.update_metrics", side_effect=requests.exceptions.HTTPError("secret-body"))
    def test_cli_error_does_not_print_server_response(self, update):
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as failure:
            metrics.main()
        self.assertNotIn("secret-body", str(failure.exception))
        self.assertIn("HTTPError", str(failure.exception))


if __name__ == "__main__":
    unittest.main()
