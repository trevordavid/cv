# Google Scholar Integration

This branch replaces the NASA ADS API with Google Scholar for retrieving citation metrics and publication information.

## Changes

- Replaced ADS API integration with the `scholarly` Python library for Google Scholar
- Updated the metrics calculation to use Google Scholar data
- Modified lead author detection based on authorship order in Google Scholar data

## Setup

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   - `GOOGLE_SCHOLAR_ID`: Your Google Scholar profile ID (optional but recommended)
   - `ORCID_ID`: Your ORCID ID (used as fallback if Google Scholar ID is not provided)

   You can find your Google Scholar ID in your profile URL: `https://scholar.google.com/citations?user=YOUR_ID_HERE`

3. Run the update script:
   ```
   python update_metrics.py
   ```

## Notes

- Google Scholar has no official API, and the `scholarly` package is a third-party library that scrapes data from Google Scholar
- Excessive use may lead to rate limiting or CAPTCHA challenges from Google
- For CI/CD deployments, consider using a proxy or implementing rate limiting to avoid blocks

## Benefits

- Wider coverage of publications compared to ADS
- More commonly used citation metrics source in many fields
- No API key needed for basic usage 