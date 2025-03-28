# Publication Metrics Integration

This branch adds support for retrieving citation metrics from both NASA ADS API and Google Scholar.

## Changes

- Added dual API support with command-line options to switch between sources
- Maintained original NASA ADS API integration for reliable lead author detection
- Added Google Scholar integration via the `scholarly` Python library
- Improved automatic lead author detection for Google Scholar data
- Added robust fallback mechanisms when data is incomplete

## Setup

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set up environment variables in `.secrets` file or your environment:
   ```
   ADS_API_KEY=your_nasa_ads_api_key
   GOOGLE_SCHOLAR_ID=your_google_scholar_id
   ORCID_ID=your_orcid_id
   ADS_LIBRARY_ID=your_ads_library_id
   ADS_LEAD_AUTHOR_LIBRARY_ID=your_ads_lead_author_library_id
   ```

3. Run the update script:
   ```
   # Using NASA ADS API (default)
   python update_metrics.py --api ads
   
   # Using Google Scholar
   python update_metrics.py --api google_scholar
   ```

## API Comparison

### NASA ADS API
- **Pros**: More accurate for academic papers, reliable lead author detection via custom libraries
- **Cons**: Requires API key, primarily focused on astronomical publications

### Google Scholar
- **Pros**: Broader coverage, no API key needed for basic usage, includes more citation sources
- **Cons**: Limited by Google's scraping protections, less reliable author position detection

## Lead Author Detection

- **ADS**: Uses a dedicated library for lead author papers
- **Google Scholar**: Uses a sample-based approach to determine the percentage of papers where you are first author

## Notes

- Google Scholar has no official API, and the `scholarly` package is a third-party library
- Excessive use of the Google Scholar API may lead to rate limiting or CAPTCHA challenges 