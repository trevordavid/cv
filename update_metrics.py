import os
import sys
import argparse
from scholarly import scholarly
import re
import json
import time

# Define API choice via command line argument
parser = argparse.ArgumentParser(description='Update publication metrics using Google Scholar or NASA ADS API')
parser.add_argument('--api', choices=['ads', 'google_scholar', 'hybrid'], default='hybrid', 
                    help='API to use for fetching metrics (default: hybrid)')
args = parser.parse_args()

# Environment variables for both APIs
ORCID_ID = os.getenv("ORCID_ID", "0000-0001-6534-6246")
GOOGLE_SCHOLAR_ID = os.getenv("GOOGLE_SCHOLAR_ID", "t12ArKcAAAAJ")
ADS_API_KEY = os.getenv("ADS_API_KEY")


# ADS library IDs
ADS_LIBRARY_ID = os.getenv("ADS_LIBRARY_ID", "jtVFaJEgTa-f_8rDodxeJg")
ADS_LEAD_AUTHOR_LIBRARY_ID = os.getenv("ADS_LEAD_AUTHOR_LIBRARY_ID", "ZGzLvEG9RgWI9xHL25CByw")

# Function to get metrics using NASA ADS API
def get_ads_metrics():
    if not ADS_API_KEY:
        raise ValueError("NASA ADS API Key is missing. Set ADS_API_KEY in GitHub Secrets.")
    
    # Import the ads module only when needed
    import ads
    ads.config.token = ADS_API_KEY
    
    # Function to query ADS library and compute metrics
    def query_library(library_id):
        query = ads.SearchQuery(
            q=f"docs(library/{library_id})",
            fl=["id", "citation_count", "read_count", "downloads", "title", "bibcode"],
            fq=["property:refereed OR property:notrefereed"],
            rows=2000
        )
        publications = list(query)
        
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
    general_metrics = query_library(ADS_LIBRARY_ID)
    lead_author_metrics = query_library(ADS_LEAD_AUTHOR_LIBRARY_ID)
    
    return {
        "total_papers": general_metrics["total_papers"],
        "total_citations": general_metrics["total_citations"],
        "h_index": general_metrics["h_index"],
        "g_index": general_metrics["g_index"],
        "i10_index": general_metrics["i10_index"],
        "lead_author_papers": lead_author_metrics["total_papers"],
        "lead_author_citations": lead_author_metrics["total_citations"]
    }

# Function to get metrics using Google Scholar
def get_google_scholar_metrics():
    try:
        print("Starting Google Scholar metrics fetch...")
        # Try to get author by ID if available
        if GOOGLE_SCHOLAR_ID:
            print(f"Searching for author with ID: {GOOGLE_SCHOLAR_ID}")
            author = scholarly.search_author_id(GOOGLE_SCHOLAR_ID)
        else:
            # Search by name and ORCID
            print(f"Searching for author with ORCID: {ORCID_ID}")
            search_query = scholarly.search_author(f"orcid:{ORCID_ID}")
            author = next(search_query)
        
        print("Found author, filling details...")
        # Fill in all available details
        author = scholarly.fill(author)
        author_name = author.get('name', '')
        print(f"Author name: {author_name}")
        
        # Extract metrics
        total_citations = author.get('citedby', 0)
        h_index = author.get('hindex', 0)
        i10_index = author.get('i10index', 0)
        
        # Get publication count
        publications = author.get('publications', [])
        total_papers = len(publications)
        print(f"Total publications found: {total_papers}")
        print(f"Total citations: {total_citations}")
        print(f"h-index: {h_index}")
        print(f"i10-index: {i10_index}")

        # Calculate g-index
        citation_counts = sorted([pub.get('num_citations', 0) for pub in publications], reverse=True)
        g_index, citation_sum = 0, 0
        for i, c in enumerate(citation_counts, start=1):
            citation_sum += c
            if citation_sum >= i**2:
                g_index = i
        print(f"g-index: {g_index}")
        
        return {
            "total_papers": total_papers,
            "total_citations": total_citations,
            "h_index": h_index,
            "g_index": g_index,
            "i10_index": i10_index
        }
    except Exception as e:
        print(f"Error retrieving Google Scholar data: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print("Full traceback:")
        print(traceback.format_exc())
        return {
            "total_papers": 0,
            "total_citations": 0,
            "h_index": 0,
            "g_index": 0,
            "i10_index": 0
        }

# Function to get metrics using hybrid approach
def get_hybrid_metrics():
    # Get first author metrics from ADS
    try:
        print("Fetching first author metrics from NASA ADS...")
        if not ADS_API_KEY:
            raise ValueError("NASA ADS API Key is missing. Set ADS_API_KEY in GitHub Secrets.")
        
        import ads
        ads.config.token = ADS_API_KEY
        
        # Get lead author library data
        query = ads.SearchQuery(
            q=f"docs(library/{ADS_LEAD_AUTHOR_LIBRARY_ID})",
            fl=["id", "citation_count", "title", "bibcode"],
            fq=["property:refereed OR property:notrefereed"],
            rows=2000
        )
        lead_publications = list(query)
        lead_author_papers = len(lead_publications)
        lead_author_citations = sum(int(pub.citation_count or 0) for pub in lead_publications)
        print(f"Found {lead_author_papers} lead author papers with {lead_author_citations} citations from NASA ADS")
        
        # Get total papers from ADS library
        total_query = ads.SearchQuery(
            q=f"docs(library/{ADS_LIBRARY_ID})",
            fl=["id", "citation_count", "title", "bibcode"],
            fq=["property:refereed OR property:notrefereed"],
            rows=2000
        )
        total_publications = list(total_query)
        total_papers = len(total_publications)
        print(f"Found {total_papers} total papers from NASA ADS")
        
        # Get overall metrics from Google Scholar
        print("\nFetching overall metrics from Google Scholar...")
        try:
            scholar_metrics = get_google_scholar_metrics()
            return {
                "total_papers": total_papers,  # Use ADS total papers count
                "total_citations": scholar_metrics["total_citations"],
                "h_index": scholar_metrics["h_index"],
                "g_index": scholar_metrics["g_index"],
                "i10_index": scholar_metrics["i10_index"],
                "lead_author_papers": lead_author_papers,
                "lead_author_citations": lead_author_citations
            }
        except Exception as e:
            print(f"Error retrieving Google Scholar data: {e}")
            print("Using ADS data for all metrics...")
            # Calculate metrics from ADS data
            citation_counts = sorted([int(pub.citation_count or 0) for pub in total_publications], reverse=True)
            h_index = sum(c >= i + 1 for i, c in enumerate(citation_counts))
            g_index, citation_sum = 0, 0
            for i, c in enumerate(citation_counts, start=1):
                citation_sum += c
                if citation_sum >= i**2:
                    g_index = i
            i10_index = sum(c >= 10 for c in citation_counts)
            total_citations = sum(citation_counts)
            
            return {
                "total_papers": total_papers,
                "total_citations": total_citations,
                "h_index": h_index,
                "g_index": g_index,
                "i10_index": i10_index,
                "lead_author_papers": lead_author_papers,
                "lead_author_citations": lead_author_citations
            }
    except Exception as e:
        print(f"Error with hybrid approach: {e}")
        print("Falling back to NASA ADS for all metrics...")
        return get_ads_metrics()

# Get metrics based on the chosen API
print(f"Using {args.api} API for publication metrics...")
if args.api == 'ads':
    metrics = get_ads_metrics()
    source = "NASA ADS API"
elif args.api == 'google_scholar':
    metrics = get_google_scholar_metrics()
    source = "Google Scholar"
    # Use placeholder values for lead author metrics since we're not calculating them
    metrics["lead_author_papers"] = 0
    metrics["lead_author_citations"] = 0
else:  # hybrid approach
    metrics = get_hybrid_metrics()
    source = "hybrid (Google Scholar + NASA ADS)"

# Write metrics to file
metrics_text = rf"""
{metrics['lead_author_papers']} lead author papers ({metrics['lead_author_citations']} citations),
{metrics['total_papers']} total papers ({metrics['total_citations']} citations).\newline
h-index: {metrics['h_index']}, g-index: {metrics['g_index']}, i10-index: {metrics['i10_index']}. Updated \today.
"""

metrics_path = "sections/publication-metrics.tex"
with open(metrics_path, "w", encoding="utf-8") as f:
    f.write(metrics_text.strip())

print(f"Updated {metrics_path} with latest publication metrics from {source}.")
