# Automated CV

This repository builds my CV with XeLaTeX and refreshes publication metrics from two NASA ADS libraries.

[Download the latest CV](https://github.com/trevordavid/cv/blob/main/cv.pdf)

## Automated builds

The GitHub Actions workflow runs daily at midnight UTC, on pushes to main, and manually from the Actions tab. Scheduled runs can be delayed by GitHub. Pull requests run the regression tests and compile with example contact details; they do not use secrets or publish changes.

Both jobs use Ubuntu 24.04 and Python 3.13 (declared in `.python-version`). The runner is explicit because changes to `ubuntu-latest` can remove support for older Python versions. Python dependencies are locked in `requirements.txt`, and GitHub Actions are pinned to commit SHAs. Dependabot checks for updates monthly.

Configure these repository Actions secrets:

- `ADS_API_KEY`: NASA ADS API token with access to the two libraries in `update_metrics.py`.
- `EMAIL`: the email address to display.
- `PHONE`: the phone number to display.

Publishing uses the automatically provided `GITHUB_TOKEN` with job-scoped `contents: write`. A personal `GH_PAT` is no longer needed. Repository rules must allow the Actions bot to push to main.

The updater retries transient ADS failures with bounded timeouts and exponential backoff. Empty, incomplete, duplicate, or invalid results stop the run before replacing the metrics. Both libraries must succeed. Optional environment variables `ADS_RETRY_ATTEMPTS` (default 4, range 1–10) and `ADS_RETRY_BASE_DELAY_SECONDS` (default 5, range 0–60) control retries.

The build runs three noninteractive XeLaTeX passes and validates the new PDF before replacing `cv.pdf`. Compilation failures cannot publish the previous PDF as a fresh result. Successful production builds upload a 30-day artifact and commit only the metrics and PDF. Runs are serialized; if main changes during a build, a normal push fails safely. Rerun the workflow against current main after such a conflict.

Contact source files and local secrets are ignored by Git. The generated PDF intentionally includes the contact details and is published to this repository.

## Local build

Install Python 3.13, XeLaTeX, and Poppler (`pdfinfo`). On Ubuntu 24.04:

```sh
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  texlive-xetex texlive-fonts-recommended texlive-fonts-extra \
  texlive-latex-extra poppler-utils
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Create `sections/private_info.tex` from the template and edit its values, or set `EMAIL` and `PHONE` in your environment and run the helper, which escapes LaTeX special characters:

```sh
cp sections/private_info.template.tex sections/private_info.tex
# Alternatively: python scripts/write_private_info.py
bash scripts/build_cv.sh
```

The build writes intermediates to ignored `build/` and updates `cv.pdf` only on success. Keep the bundled font files in place.

To refresh metrics first, set `ADS_API_KEY` in your environment, then run:

```sh
python update_metrics.py
bash scripts/build_cv.sh
```

No credentials are needed for the offline regression tests:

```sh
python -m unittest discover -s tests -v
```

After changing `requirements.in`, regenerate the lock file with [uv](https://docs.astral.sh/uv/):

```sh
uv pip compile requirements.in --python-version 3.13 --output-file requirements.txt
```
