import os
import time

import ads
import requests
from ads.exceptions import APIResponseError

# Get API key and ORCID from GitHub Secrets
ADS_API_KEY = os.getenv("ADS_API_KEY")
#ORCID_ID = os.getenv("ORCID_ID")
ORCID_ID = "0000-0001-6534-6246"
LIBRARY_ID = "jtVFaJEgTa-f_8rDodxeJg"
LEAD_AUTHOR_LIBRARY_ID = "ZGzLvEG9RgWI9xHL25CByw"

if not ADS_API_KEY:
    raise ValueError("NASA ADS API Key is missing. Set ADS_API_KEY in GitHub Secrets.")
if not ORCID_ID:
    raise ValueError("ORCID ID is missing. Set ORCID_ID in GitHub Secrets.")

ads.config.token = ADS_API_KEY

ADS_RETRY_ATTEMPTS = max(1, int(os.getenv("ADS_RETRY_ATTEMPTS", "4")))
ADS_RETRY_BASE_DELAY_SECONDS = max(0.0, float(os.getenv("ADS_RETRY_BASE_DELAY_SECONDS", "5")))


def is_retryable_ads_error(exc):
    if isinstance(exc, requests.exceptions.RequestException):
        return True

    message = str(exc).lower()
    retryable_markers = (
        "429",
        "500",
        "502",
        "503",
        "504",
        "bad gateway",
        "gateway time-out",
        "service unavailable",
        "temporarily unavailable",
        "timed out",
    )
    return any(marker in message for marker in retryable_markers)


def fetch_publications(library_id):
    last_error = None

    for attempt in range(1, ADS_RETRY_ATTEMPTS + 1):
        query = ads.SearchQuery(
            q=f"docs(library/{library_id})",
            fl=["id", "citation_count", "read_count", "downloads", "title", "bibcode"],
            fq=["property:refereed OR property:notrefereed"],
            rows=2000,
        )

        try:
            return list(query)
        except (APIResponseError, requests.exceptions.RequestException) as exc:
            last_error = exc
            if attempt == ADS_RETRY_ATTEMPTS or not is_retryable_ads_error(exc):
                raise

            delay_seconds = ADS_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
            print(
                f"Attempt {attempt}/{ADS_RETRY_ATTEMPTS} for library {library_id} failed: {exc}. "
                f"Retrying in {delay_seconds:.1f}s."
            )
            time.sleep(delay_seconds)

    raise last_error

# Function to query ADS library and compute metrics
def get_metrics(library_id):
    publications = fetch_publications(library_id)
    
    total_papers = len(publications)
    total_citations = sum(int(pub.citation_count or 0) for pub in publications)
    total_reads = sum(int(pub.read_count or 0) for pub in publications)
    total_downloads = sum(int(pub.downloads or 0) for pub in publications)
    
    sorted_citations = sorted((int(pub.citation_count or 0) for pub in publications), reverse=True)
    h_index = sum(c >= i + 1 for i, c in enumerate(sorted_citations))
    
    g_index, citation_sum = 0, 0
    for i, c in enumerate(sorted_citations, start=1):
        citation_sum += c
        if citation_sum >= i**2:
            g_index = i
    
    i10_index = sum(c >= 10 for c in sorted_citations)
    
    return {
        "total_papers": total_papers,
        "total_citations": total_citations,
        "total_reads": total_reads,
        "total_downloads": total_downloads,
        "h_index": h_index,
        "g_index": g_index,
        "i10_index": i10_index,
    }

# Get metrics for both general and lead author libraries
general_metrics = get_metrics(LIBRARY_ID)
lead_author_metrics = get_metrics(LEAD_AUTHOR_LIBRARY_ID)

# Write metrics to file
metrics_text = rf"""
{lead_author_metrics['total_papers']} lead author papers ({lead_author_metrics['total_citations']} citations),
{general_metrics['total_papers']} total papers ({general_metrics['total_citations']} citations).\newline
h-index: {general_metrics['h_index']}, g-index: {general_metrics['g_index']}, i10-index: {general_metrics['i10_index']}. Updated \today.
"""

metrics_path = "sections/publication-metrics.tex"
with open(metrics_path, "w", encoding="utf-8") as f:
    f.write(metrics_text.strip())

print(f"Updated {metrics_path} with latest publication metrics.")
