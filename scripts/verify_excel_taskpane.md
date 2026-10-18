# Isolated Excel task-pane browser test

This test loads the actual task-pane HTML, CSS, JavaScript, evidence parser and
insertion adapter. It substitutes an in-memory Excel host and the repository's
synthetic research fixtures. It never connects to a signed-in browser, Microsoft
account or live research API. It is browser integration QA, not native Excel
acceptance or adoption measurement.

Requirements: Python 3.10+, Node 20+, `playwright==1.64.0`, and an installed
Chromium/Chrome executable. No Office application, Docker, API key, browser
extension or package build is needed. Install dependencies only in the test
environment; do not create a browser profile from a user's existing profile.

```sh
python scripts/verify_excel_taskpane.py \
  --browser /path/to/chrome-or-chromium \
  --output /path/to/evidence
```

On this workspace, the existing SSD verification environment can run it without
installing anything:

```sh
/Users/mrinal/SSDWorkspace/evidence/office-linux-20261018/venv/bin/python \
  scripts/verify_excel_taskpane.py \
  --output /Users/mrinal/SSDWorkspace/evidence/office-completion-20261018/marketplaces
```

The script creates a temporary loopback HTTP server on an available port and a
fresh headless browser context. All non-local network requests are intercepted:
Office.js receives a bounded host mock, the research API receives fixture JSON,
and unexpected destinations are blocked and fail the test. Output includes a
JSON receipt with source hashes, success/error screenshots, and downloaded fixture
evidence under the prefix `excel-taskpane-local`. Re-running replaces only these
test output files in the chosen directory.

Checks cover a 320-pixel pane, keyboard focus, no requests on open or invalid
selection, five-row previews, typed zero/missing/negative/withheld values,
formula-looking source text, JSON download, six new sheets per insertion,
preservation of existing analysis, repeated insertions, stale-capture clearing,
partial and total request failures, and unsupported-host insertion blocking.
Root CI should install the pinned test requirements and pass its browser path
explicitly; no existing workflow is modified by this script.
