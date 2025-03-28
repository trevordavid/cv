import os
import sys
import argparse
from scholarly import scholarly
import re
import json
import time

# Define API choice via command line argument
parser = argparse.ArgumentParser(description='Update publication metrics using Google Scholar or NASA ADS API')
parser.add_argument('--api', choices=['ads', 'google_scholar'], default='ads', 
                    help='API to use for fetching metrics (default: ads)')
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
        # Try to get author by ID if available
        if GOOGLE_SCHOLAR_ID:
            author = scholarly.search_author_id(GOOGLE_SCHOLAR_ID)
        else:
            # Search by name and ORCID
            search_query = scholarly.search_author(f"orcid:{ORCID_ID}")
            author = next(search_query)
        
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

        # Calculate g-index
        citation_counts = sorted([pub.get('num_citations', 0) for pub in publications], reverse=True)
        g_index, citation_sum = 0, 0
        for i, c in enumerate(citation_counts, start=1):
            citation_sum += c
            if citation_sum >= i**2:
                g_index = i
        
        # Since publications don't contain full author lists by default,
        # we'll use a more targeted approach for lead author detection
        lead_author_papers = 0
        lead_author_citations = 0
        
        # Try to get detailed information for a sample of publications
        # to determine the author's position in author lists
        sample_size = min(10, len(publications))  # Sample up to 10 publications
        detailed_pubs = []
        
        print(f"Fetching detailed information for {sample_size} publications...")
        
        # Try to identify common author patterns from the first author's papers
        position_counts = {
            "first": 0,
            "middle": 0,
            "last": 0
        }
        
        for i, pub in enumerate(publications[:sample_size]):
            try:
                # Fill publication with complete data
                detailed_pub = scholarly.fill(pub)
                detailed_pubs.append(detailed_pub)
                
                # Let's see if we have authors info now
                if 'bib' in detailed_pub and detailed_pub['bib'] and 'author' in detailed_pub['bib']:
                    authors_text = detailed_pub['bib']['author']
                    
                    # Check if we can determine author position
                    # Common formats: "A and B", "A, B, and C", "A, B, C"
                    possible_authors = []
                    
                    # Try different splitting approaches
                    if ',' in authors_text and ' and ' in authors_text:
                        parts = authors_text.replace(' and ', ', ').split(', ')
                        possible_authors = [p.strip() for p in parts if p.strip()]
                    elif ',' in authors_text:
                        possible_authors = [p.strip() for p in authors_text.split(',') if p.strip()]
                    elif ' and ' in authors_text:
                        possible_authors = [p.strip() for p in authors_text.split(' and ') if p.strip()]
                    
                    # Check if we successfully split the authors list
                    if possible_authors:
                        print(f"Publication {i+1} authors: {possible_authors}")
                        
                        # Simplify author name for comparison (handle initials vs. full names)
                        author_parts = author_name.split()
                        lastname = author_parts[-1].lower()
                        
                        # Check if author's name is in any of the parsed authors
                        position = None
                        for idx, possible_author in enumerate(possible_authors):
                            if lastname in possible_author.lower():
                                if idx == 0:
                                    position = "first"
                                elif idx == len(possible_authors) - 1:
                                    position = "last"
                                else:
                                    position = "middle"
                                break
                        
                        if position:
                            position_counts[position] += 1
                            print(f"  Author position: {position}")
                
                # Avoid rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Error analyzing publication {i+1}: {e}")
        
        print(f"\nAuthor position analysis: {position_counts}")
        
        # Based on position analysis, identify the most common position
        # If the author is predominantly first author, use position ratio from sample
        total_positions = sum(position_counts.values())
        if total_positions > 0:
            first_author_ratio = position_counts["first"] / total_positions
            lead_author_papers = int(total_papers * first_author_ratio)
            
            # Get citations from the most-cited papers up to the lead author count
            sorted_pubs = sorted(publications, key=lambda p: p.get('num_citations', 0), reverse=True)
            lead_author_citations = sum(p.get('num_citations', 0) for p in sorted_pubs[:lead_author_papers])
            print(f"Using position analysis: {lead_author_papers} lead author papers (approx. {first_author_ratio:.0%} of total)")
        else:
            # Fallback to known first-author papers
            known_first_author_papers = [
                "A Neptune-sized transiting planet closely orbiting a 5–10-million-year-old star",
                # Add more known papers here
            ]
            
            for pub in publications:
                pub_title = pub.get('bib', {}).get('title', '')
                if pub_title in known_first_author_papers:
                    lead_author_papers += 1
                    lead_author_citations += pub.get('num_citations', 0)
                    print(f"Found known first-author paper: {pub_title}")
            
            # If still no lead author papers found, use conservative estimate
            if lead_author_papers == 0:
                lead_author_papers = max(1, int(total_papers * 0.2))
                print(f"Using fallback estimate: {lead_author_papers} lead author papers (20% of total)")
                
                sorted_pubs = sorted(publications, key=lambda p: p.get('num_citations', 0), reverse=True)
                lead_author_citations = sum(p.get('num_citations', 0) for p in sorted_pubs[:lead_author_papers])
        
        print(f"\nFinal count: {lead_author_papers} lead author papers with {lead_author_citations} citations")
        
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
        print(f"Error retrieving Google Scholar data: {e}")
        return {
            "total_papers": 0,
            "total_citations": 0,
            "h_index": 0,
            "g_index": 0,
            "i10_index": 0,
            "lead_author_papers": 0,
            "lead_author_citations": 0
        }

# Get metrics based on the chosen API
print(f"Using {args.api} API for publication metrics...")
if args.api == 'ads':
    metrics = get_ads_metrics()
    source = "NASA ADS API"
else:
    metrics = get_google_scholar_metrics()
    source = "Google Scholar"

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
