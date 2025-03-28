# Hybrid Publication Metrics Integration

This branch adds a hybrid approach for retrieving citation metrics, leveraging the strengths of both NASA ADS API and Google Scholar.

## Hybrid Approach

- **First Author Metrics**: NASA ADS API (more accurate for lead author detection)
- **Overall Citations & Metrics**: Google Scholar (broader coverage across disciplines)

## Changes

- Added hybrid approach that combines the best of both APIs
- Maintained NASA ADS for lead author paper detection via custom libraries
- Added Google Scholar integration for overall citation metrics
- Added command-line options to switch between API sources
- Updated GitHub Actions workflow to use the hybrid approach by default

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
   # Using the hybrid approach (default)
   python update_metrics.py --api hybrid
   
   # Using only NASA ADS API
   python update_metrics.py --api ads
   
   # Using only Google Scholar
   python update_metrics.py --api google_scholar
   ```

## API Comparison

### NASA ADS API
- **Pros**: More accurate for academic papers, reliable lead author detection via custom libraries
- **Cons**: Requires API key, primarily focused on astronomical publications

### Google Scholar
- **Pros**: Broader coverage, no API key needed for basic usage, includes more citation sources
- **Cons**: Limited by Google's scraping protections, less reliable author position detection

### Hybrid (Default)
- **Pros**: Gets the best of both worlds - accurate first author detection and broader citation coverage
- **Cons**: Requires both APIs to be set up and working

## Notes

- Google Scholar has no official API, and the `scholarly` package is a third-party library
- Excessive use of the Google Scholar API may lead to rate limiting or CAPTCHA challenges
- The GitHub Actions workflow is configured to use the hybrid approach by default 