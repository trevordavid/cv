import os
from scholarly import scholarly

# Get API key and ORCID from GitHub Secrets
ORCID_ID = os.getenv("ORCID_ID", "0000-0001-6534-6246")
GOOGLE_SCHOLAR_ID = os.getenv("GOOGLE_SCHOLAR_ID")

if not GOOGLE_SCHOLAR_ID:
    print("Warning: Google Scholar ID not found in environment variables. Using profile search instead.")

# Function to get author data from Google Scholar
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
        
        # Extract metrics
        total_citations = author.get('citedby', 0)
        h_index = author.get('hindex', 0)
        i10_index = author.get('i10index', 0)
        
        # Get publication count
        publications = author.get('publications', [])
        total_papers = len(publications)

        # Filter for lead author papers (where author is first in the list)
        lead_author_papers = 0
        lead_author_citations = 0
        
        # Calculate g-index
        # Sort citations in descending order
        citation_counts = sorted([pub.get('num_citations', 0) for pub in publications], reverse=True)
        g_index, citation_sum = 0, 0
        for i, c in enumerate(citation_counts, start=1):
            citation_sum += c
            if citation_sum >= i**2:
                g_index = i
                
        # Count lead author papers (assuming first author is lead)
        for pub in publications:
            if pub.get('bib') and pub.get('bib').get('author'):
                authors = pub.get('bib').get('author').split(' and ')
                if authors and authors[0] == author.get('name'):
                    lead_author_papers += 1
                    lead_author_citations += pub.get('num_citations', 0)
        
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

# Get metrics from Google Scholar
metrics = get_google_scholar_metrics()

# Write metrics to file
metrics_text = rf"""
{metrics['lead_author_papers']} lead author papers ({metrics['lead_author_citations']} citations),
{metrics['total_papers']} total papers ({metrics['total_citations']} citations).\newline
h-index: {metrics['h_index']}, g-index: {metrics['g_index']}, i10-index: {metrics['i10_index']}. Updated \today.
"""

metrics_path = "sections/publication-metrics.tex"
with open(metrics_path, "w", encoding="utf-8") as f:
    f.write(metrics_text.strip())

print(f"Updated {metrics_path} with latest publication metrics from Google Scholar.")
