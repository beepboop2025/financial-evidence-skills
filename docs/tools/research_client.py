#!/usr/bin/env python3
"""Capture cited research tables for Python, notebooks, spreadsheets and SQL.

Uses only Python 3.10+ standard libraries. Reads the public hosted backend;
does not install software, schedule polling, send messages or submit trades.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE_URL = "https://api.seiche.info/openbb"
DATASETS = (
    "money_markets", "money_market_history", "capital_markets", "bank_risk",
    "market_liquidity", "china_economy", "source_health",
)
DEFAULT_DESK = ("money_markets", "bank_risk", "market_liquidity")
MAX_BYTES = 4 * 1024 * 1024


class EvidenceError(ValueError):
    """The response cannot form a complete, consistent capture."""


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise EvidenceError("Unexpected redirect; check the documented backend URL")


def _json(raw):
    def reject(value):
        raise EvidenceError(f"Non-finite JSON number: {value}")
    result = json.loads(raw, parse_constant=reject)
    # Also rejects finite JSON notation overflowing Python floats (e.g. 1e999).
    json.dumps(result, allow_nan=False)
    return result


def _page(params, *, synthetic=False, opener=None):
    headers = {"Accept": "application/json", "User-Agent": "Financial-Evidence-Research-Desk/1.0"}
    if synthetic:
        headers.update({"User-Agent": "Financial-Evidence-Operator-Verification/1.0",
                        "X-Liquilens-Traffic-Class": "synthetic"})
    request = Request(BASE_URL + "/api/v1/query?" + urlencode(params), headers=headers)
    open_request = opener or build_opener(_NoRedirects()).open
    with open_request(request, timeout=20) as response:
        if response.headers.get_content_type() != "application/json":
            raise EvidenceError("Expected JSON; received a challenge or unexpected content")
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise EvidenceError("Response exceeds the 4 MiB capture limit")
    result = _json(raw)
    if not isinstance(result, dict) or result.get("schema") != "liquidity-lab.openbb-table.v1":
        raise EvidenceError("Unsupported table schema")
    if result.get("transport_status") != "complete":
        raise EvidenceError("Source retrieval is incomplete; inspect /api/v1/sources before capturing")
    if result.get("evidence_status") != "not_evaluated" or result.get("carrier_verification") != "not_performed":
        raise EvidenceError("Unexpected evidence authority contract")
    return result


def _signature(page):
    sources = page.get("sources")
    if not isinstance(sources, list) or not sources:
        raise EvidenceError("Missing source provenance")
    identities = []
    for source in sources:
        if not isinstance(source, dict):
            raise EvidenceError("Malformed source provenance")
        url, digest = source.get("source_url"), source.get("content_sha256")
        if not isinstance(url, str) or not url.startswith("https://"):
            raise EvidenceError("Missing HTTPS source identity")
        if not isinstance(digest, str) or not re.fullmatch(r"(?:sha256:)?[a-f0-9]{64}", digest):
            raise EvidenceError("Missing source content hash")
        identities.append((url, digest))
    return tuple(sorted(identities))


def collect(dataset, *, entity="", start_date="", end_date="", page_size=200,
            max_pages=10, synthetic=False, opener=None):
    """Follow bounded pagination, refusing to mix changed source documents.

    Restricted and unavailable numeric rows remain null. Completed retrieval is
    not a judgment of freshness, redistribution rights or suitability.
    """
    if dataset not in DATASETS or not isinstance(entity, str) or len(entity) > 100:
        raise ValueError("Choose a supported dataset and an entity substring of at most 100 characters")
    if type(page_size) is not int or not 1 <= page_size <= 2000:
        raise ValueError("page_size must be 1..2000")
    if type(max_pages) is not int or not 1 <= max_pages <= 20:
        raise ValueError("max_pages must be 1..20")
    for value in (start_date, end_date):
        if not isinstance(value, str) or (value and (
                not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) or not date.fromisoformat(value))):
            raise ValueError("Use YYYY-MM-DD observation dates")
    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date must not exceed end_date")
    params = dict(dataset=dataset, entity=entity, start_date=start_date,
                  end_date=end_date, limit=page_size, offset=0)
    rows, pages, signature, expected_total = [], [], None, None
    for _ in range(max_pages):
        page = _page(params, synthetic=synthetic, opener=opener)
        batch = page.get("results")
        total = page.get("total_rows")
        if (page.get("dataset") != dataset or page.get("offset") != params["offset"]
                or page.get("limit") != page_size or not isinstance(batch, list)
                or any(type(page.get(key)) is not int for key in ("offset", "limit", "returned_rows"))
                or "next_offset" not in page
                or any(not isinstance(row, dict) or row.get("dataset") != dataset for row in batch)
                or type(total) is not int or total < 0
                or page.get("returned_rows") != len(batch) or len(batch) > page_size):
            raise EvidenceError("Invalid pagination or row identity")
        current_signature = _signature(page)
        if signature is not None and (signature != current_signature or expected_total != total):
            raise EvidenceError("Source snapshot changed between pages; restart the capture")
        signature, expected_total = current_signature, total
        rows.extend(batch)
        pages.append({key: value for key, value in page.items() if key != "results"})
        next_offset = page.get("next_offset")
        if next_offset is None:
            if len(rows) != expected_total:
                raise EvidenceError("Incomplete row count at the end of pagination")
            return {
                "schema": "financial-evidence.research-capture.v1", "dataset": dataset,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "request": {k: v for k, v in params.items() if k != "offset"},
                "results": rows, "returned_rows": len(rows), "pages": pages,
                "transport_status": "complete", "evidence_status": "not_evaluated",
                "carrier_verification": "not_performed", "financial_authority": "none",
                "history_scope": "currently_published_not_as_published_vintages",
            }
        if type(next_offset) is not int or not batch or next_offset != len(rows) or next_offset >= total:
            raise EvidenceError("Invalid or non-advancing next_offset")
        params["offset"] = next_offset
    raise EvidenceError("Capture exceeds max_pages; narrow the entity/date filters or increase the explicit bound")


def _csv_cell(value):
    if isinstance(value, str) and (value.startswith(("\t", "\r", "\n"))
                                  or value.lstrip().startswith(("=", "+", "-", "@"))):
        return "'" + value
    return value


def save_capture(capture, directory):
    """Save original JSON, spreadsheet-safe CSV and hashes in a new directory."""
    directory = Path(directory)
    rows = capture["results"]
    fields = sorted({key for row in rows for key in row}) or ["dataset", "value", "as_of", "availability", "source_url"]
    if any(not re.fullmatch(r"[a-z][a-z0-9_]*", name) for name in fields):
        raise EvidenceError("Unexpected column names")
    raw = (json.dumps(capture, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "evidence.json").write_bytes(raw)
    with (directory / "rows.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: _csv_cell(value) for key, value in row.items()} for row in rows)
    receipt = {
        "dataset": capture["dataset"], "captured_at": capture["captured_at"],
        "row_count": len(rows), "pages_read": len(capture["pages"]),
        "csv_policy": "nulls_empty_formula_strings_escaped_original_values_in_json",
        "sha256": {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                   for name in ("evidence.json", "rows.csv")},
        "external_user_or_payment_verified": False,
    }
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=("desk", *DATASETS), nargs="?", default="desk")
    parser.add_argument("--entity", default="")
    parser.add_argument("--start-date", default="")
    parser.add_argument("--end-date", default="")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--synthetic", action="store_true", help="Identify operator/CI verification traffic")
    args = parser.parse_args()
    if args.dataset == "desk" and args.entity:
        parser.error("Use an individual dataset for an entity filter")
    datasets = DEFAULT_DESK if args.dataset == "desk" else (args.dataset,)
    captures = [collect(name, entity=args.entity, start_date=args.start_date,
                        end_date=args.end_date, synthetic=args.synthetic) for name in datasets]
    args.output.mkdir(parents=True, exist_ok=False)
    for capture in captures:
        print(json.dumps(save_capture(capture, args.output / capture["dataset"])))


if __name__ == "__main__":
    main()
