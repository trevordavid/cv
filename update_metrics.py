"""Fetch complete ADS libraries and atomically update the CV's metrics."""

import math
import os
from pathlib import Path
import re
import tempfile
import time

import ads
import requests
from ads.exceptions import APIResponseError

LIBRARY_ID = "jtVFaJEgTa-f_8rDodxeJg"
LEAD_AUTHOR_LIBRARY_ID = "ZGzLvEG9RgWI9xHL25CByw"
METRICS_PATH = Path(__file__).resolve().parent / "sections/publication-metrics.tex"
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


class TimeoutAdapter(requests.adapters.HTTPAdapter):
    """The ADS client otherwise makes requests with no timeout."""

    def send(self, request, **kwargs):
        if kwargs.get("timeout") is None:
            kwargs["timeout"] = (10, 30)
        response = super().send(request, **kwargs)
        # Preserve HTTP status codes, which ads would discard in APIResponseError.
        response.raise_for_status()
        return response


def is_retryable_ads_error(exc):
    if isinstance(exc, requests.exceptions.HTTPError):
        return exc.response is not None and exc.response.status_code in RETRYABLE_STATUSES
    if isinstance(exc, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
        return True
    if isinstance(exc, APIResponseError):
        return bool(re.search(r"\b(429|500|502|503|504)\b", str(exc)))
    return False


def fetch_publications(library_id, token, attempts=4, base_delay=5):
    for attempt in range(1, attempts + 1):
        query = ads.SearchQuery(
            q=f"docs(library/{library_id})",
            fl=["id", "citation_count", "read_count", "downloads", "bibcode"],
            fq=["property:refereed OR property:notrefereed"],
            rows=2000,
            max_pages=100,
            token=token,
        )
        try:
            with query.session as session:
                session.mount("https://", TimeoutAdapter())
                publications = list(query)
            if not publications or len(publications) != query.response.numFound:
                raise ValueError(f"ADS returned an empty or incomplete library: {library_id}")
            bibcodes = [pub.bibcode for pub in publications]
            if not all(bibcodes) or len(set(bibcodes)) != len(bibcodes):
                raise ValueError(f"ADS returned missing or duplicate bibcodes: {library_id}")
            return publications
        except (APIResponseError, requests.exceptions.RequestException) as exc:
            if attempt == attempts or not is_retryable_ads_error(exc):
                raise
            delay = base_delay * 2 ** (attempt - 1)
            # Do not log response bodies, request headers, or API credentials.
            print(f"ADS attempt {attempt}/{attempts} failed; retrying in {delay:.1f}s.")
            time.sleep(delay)


def count(value):
    if value is None:
        return 0
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]+", str(value)):
        raise ValueError("ADS returned an invalid metric count.")
    return int(value)


def calculate_metrics(publications):
    citations = sorted((count(pub.citation_count) for pub in publications), reverse=True)
    g_index, citation_sum = 0, 0
    for i, citations_for_paper in enumerate(citations, start=1):
        citation_sum += citations_for_paper
        if citation_sum >= i ** 2:
            g_index = i
    return {
        "total_papers": len(publications),
        "total_citations": sum(citations),
        "total_reads": sum(count(pub.read_count) for pub in publications),
        "total_downloads": sum(count(pub.downloads) for pub in publications),
        "h_index": sum(c >= i for i, c in enumerate(citations, start=1)),
        "g_index": g_index,
        "i10_index": sum(c >= 10 for c in citations),
    }


def update_metrics(token, destination=METRICS_PATH, attempts=4, base_delay=5):
    if not token or not token.strip():
        raise ValueError("NASA ADS API key is missing. Set ADS_API_KEY.")
    if not 1 <= attempts <= 10 or not math.isfinite(base_delay) or not 0 <= base_delay <= 60:
        raise ValueError("ADS retries must be 1-10 attempts with a finite 0-60 second base delay.")
    general = calculate_metrics(fetch_publications(LIBRARY_ID, token, attempts, base_delay))
    lead = calculate_metrics(fetch_publications(LEAD_AUTHOR_LIBRARY_ID, token, attempts, base_delay))
    if lead["total_papers"] > general["total_papers"] or lead["total_citations"] > general["total_citations"]:
        raise ValueError("Lead-author metrics exceed the general library; refusing to publish.")
    metrics_text = (
        f"{lead['total_papers']} lead author papers ({lead['total_citations']} citations),\n"
        f"{general['total_papers']} total papers ({general['total_citations']} citations)."
        + r"\newline" + "\n"
        + f"h-index: {general['h_index']}, g-index: {general['g_index']}, "
        + f"i10-index: {general['i10_index']}. Updated " + r"\today." + "\n"
    )
    destination = Path(destination)
    if destination.exists() and destination.read_text(encoding="utf-8") == metrics_text:
        print("Publication metrics are unchanged.")
        return
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(metrics_text)
        temporary_path.replace(destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    print("Updated publication metrics.")


def main():
    try:
        update_metrics(
            os.getenv("ADS_API_KEY"),
            attempts=int(os.getenv("ADS_RETRY_ATTEMPTS", "4")),
            base_delay=float(os.getenv("ADS_RETRY_BASE_DELAY_SECONDS", "5")),
        )
    except Exception as exc:
        # ADS/requests exceptions can contain server-supplied text. Keep CI logs
        # free of credentials and leave the existing metrics untouched on failure.
        raise SystemExit(f"Metrics update failed ({type(exc).__name__}); existing metrics preserved.") from None


if __name__ == "__main__":
    main()
