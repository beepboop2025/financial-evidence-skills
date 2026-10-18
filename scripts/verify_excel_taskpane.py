#!/usr/bin/env python3
"""Exercise the actual Excel task pane with a mocked host and fixture-only HTTP."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import threading
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OFFICE_CDN = "https://appsforoffice.microsoft.com/lib/1/hosted/office.js"
API_BASE = "https://agents.seiche.info/v1/research/api/v1/"
MOCK_HOST = r"""
(() => {
  const original = {name: 'My analysis', cells: [['Keep my analysis', 42]]};
  const records = [original];
  window.__excelMock = {records, original: JSON.stringify(original), syncs: 0};
  const collection = {
    items: records,
    load: property => { if (property !== 'items/name') throw Error('Unexpected workbook read'); },
    add: name => {
      if (records.some(sheet => sheet.name.toLowerCase() === name.toLowerCase())) throw Error('Duplicate sheet');
      const sheet = {name, ranges: {}};
      sheet.getRange = address => {
        if (!sheet.ranges[address]) sheet.ranges[address] = {format: {fill: {}, font: {}}};
        return sheet.ranges[address];
      };
      records.push(sheet); return sheet;
    }
  };
  window.Excel = {run: async fn => fn({workbook: {worksheets: collection},
    sync: async () => { window.__excelMock.syncs++; }})};
  window.Office = {HostType: {Excel: 'Excel'},
    context: {requirements: {isSetSupported: (set, version) => !window.__unsupportedHost && set === 'ExcelApi' && version === '1.1'}},
    onReady: fn => Promise.resolve().then(() => fn({host: window.__unsupportedHost ? 'Word' : 'Excel'}))};
})();
"""


def fixture_data():
    source = r"""
const f=require(process.argv[1]);
const rows=[f.row(0),f.row(null),f.row(-2),f.row(99,{rights_status:'metadata_only'}),
  f.row(1,{context:'=2+3'}),f.row(2),f.row(3)];
console.log(JSON.stringify({funding:f.funding('USD',rows),institutions:f.institutions()}));
"""
    return json.loads(subprocess.check_output(
        ["node", "-e", source, str(ROOT / "tests/office-fixtures.cjs")], text=True))


def run(args):
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    prefix = output / "excel-taskpane-local"
    receipt = {
        "schema": "financial-evidence.excel-taskpane-local.v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Actual task-pane UI and adapter; simulated Office.js host and fixture API responses",
        "native_excel_acceptance": False,
        "live_research_requests": 0,
        "independent_adoption_claim": False,
        "checks": [],
        "source_sha256": {},
    }
    for name in ["office-core.js", "excel/insert.js", "excel/taskpane.html", "excel/taskpane.js", "excel/taskpane.css"]:
        receipt["source_sha256"][name] = hashlib.sha256((ROOT / "docs/office" / name).read_bytes()).hexdigest()
    fixtures = fixture_data()
    receipt["fixture_sha256"] = hashlib.sha256(json.dumps(fixtures, sort_keys=True).encode()).hexdigest()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *handler_args, **kwargs):
            super().__init__(*handler_args, directory=str(ROOT / "docs"), **kwargs)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    local = f"http://127.0.0.1:{server.server_port}"
    network = {"mode": "success", "requests": [], "unexpected": []}
    errors = []

    def route_request(route):
        url = route.request.url
        if url.startswith(local + "/"):
            route.continue_()
        elif url == OFFICE_CDN:
            route.fulfill(status=200, content_type="application/javascript", body=MOCK_HOST)
        elif url.startswith(API_BASE):
            # Every API request is intercepted. No operator or user traffic leaves this test.
            if route.request.method == "OPTIONS":
                route.fulfill(status=204, headers={"Access-Control-Allow-Origin": local,
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Access-Control-Allow-Headers": "X-Liquilens-Traffic-Class, X-Financial-Evidence-Traffic-Class"})
                return
            query = parse_qs(urlparse(url).query)
            selection = query.get("selection", [""])[0]
            workflow = query.get("workflow", [""])[0]
            network["requests"].append({"url": url, "method": route.request.method,
                "headers": route.request.headers, "mode": network["mode"]})
            if network["mode"] == "all_failed" or (network["mode"] == "partial" and selection == "USD"):
                route.fulfill(status=503, content_type="application/json", body='{"error":"fixture unavailable"}',
                              headers={"Access-Control-Allow-Origin": local})
                return
            payload = copy.deepcopy(fixtures[workflow])
            payload["selection"] = selection
            route.fulfill(status=200, content_type="application/json", body=json.dumps(payload),
                          headers={"Access-Control-Allow-Origin": local})
        else:
            network["unexpected"].append(url)
            route.abort()

    def checked(name):
        receipt["checks"].append(name)

    browser = None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=args.browser, headless=True, args=["--disable-gpu"])
            context = browser.new_context(viewport={"width": 320, "height": 960}, device_scale_factor=1,
                                          accept_downloads=True)
            context.route("**/*", route_request)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(local + "/office/excel/taskpane.html?operator=1", wait_until="networkidle")
            page.get_by_text("Connected to Excel. Insertions create new sheets.").wait_for()
            assert not network["requests"], "Opening the task pane unexpectedly fetched research"
            assert page.locator("#insert").is_disabled()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            checked("no_research_on_load_and_320px_layout")

            page.locator("#currencies").focus()
            page.keyboard.press("Tab")
            assert page.locator("#institutions").evaluate("el => el === document.activeElement")
            page.keyboard.press("Tab")
            assert page.locator("#refresh").evaluate("el => el === document.activeElement")
            assert page.locator("#refresh").evaluate("el => getComputedStyle(el).outlineStyle !== 'none'")
            assert page.locator("#status").get_attribute("aria-live") == "polite"
            checked("keyboard_order_visible_focus_and_live_status")

            page.locator("#currencies").fill("USD,EUR,INR,GBP,JPY,CAD")
            page.locator("#institutions").fill("")
            page.locator("#refresh").click()
            page.wait_for_function("document.getElementById('status').textContent.includes('at most five')")
            assert not network["requests"] and page.locator("#review").is_hidden()
            assert not page.locator("#currencies").is_disabled()
            checked("invalid_selection_no_request_or_capture")

            page.locator("#currencies").fill("USD,EUR")
            page.locator("#institutions").fill("au-sfb,unknown-bank")
            page.locator("#refresh").click()
            page.locator("#review").wait_for(state="visible")
            assert len(network["requests"]) == 3
            assert "Funding: 14 rows" in page.locator("#summary").inner_text()
            assert page.locator("#preview details").count() == 3
            page.get_by_text("Funding preview", exact=True).click()
            assert page.locator("#preview details").first.locator("tr").count() == 6
            funding_cells = page.locator("#preview details").first.locator("tr").nth(1).locator("td").all_inner_texts()
            assert funding_cells[2] == "0"
            assert page.locator("#preview details").first.locator("tr").nth(2).locator("td").nth(2).inner_text() == "—"
            page.get_by_text("Institutions preview", exact=True).click()
            assert "unknown-bank" in page.locator("#preview").inner_text()
            assert "not_covered" in page.locator("#preview").inner_text()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            page.screenshot(path=str(prefix) + "-success.png", full_page=True)
            checked("bounded_preview_values_gaps_and_no_page_overflow")

            with page.expect_download() as download_info:
                page.locator("#evidence").click()
            download = download_info.value
            assert download.suggested_filename == "financial-evidence.json"
            download_path = str(prefix) + "-evidence.json"
            download.save_as(download_path)
            captured = json.loads(Path(download_path).read_text())
            assert len(captured["requests"]) == 3
            assert captured["requests"][0]["original"]["evidence"]["results"][1]["value"] is None
            assert captured["requests"][0]["original"]["evidence"]["results"][3]["value"] == 99
            assert all(row["status"]["request_status"] == "returned" for row in captured["requests"])
            checked("download_preserves_original_evidence")

            page.locator("#insert").click()
            page.wait_for_function("window.__excelMock.records.length === 7")
            page.wait_for_function("!document.getElementById('insert').disabled")
            state = page.evaluate("JSON.parse(JSON.stringify(window.__excelMock))")
            assert json.dumps(state["records"][0], separators=(",", ":")) == state["original"]
            funding_sheet = next(sheet for sheet in state["records"][1:] if sheet["name"].endswith("Funding"))
            written = next(value for value in funding_sheet["ranges"].values() if "values" in value)
            columns = written["values"][0]
            value_index, context_index = columns.index("value"), columns.index("context")
            assert written["values"][1][value_index] == 0
            assert written["values"][2][value_index] == ""
            assert written["values"][3][value_index] == -2
            assert written["values"][4][value_index] == ""
            assert written["values"][5][context_index] == "'=2+3"
            assert written["numberFormat"][1][columns.index("as_of")] == "@"
            assert written["numberFormat"][1][value_index] == "General"
            page.locator("#insert").click()
            page.wait_for_function("window.__excelMock.records.length === 13")
            page.wait_for_function("!document.getElementById('insert').disabled")
            assert page.evaluate("new Set(window.__excelMock.records.map(s => s.name.toLowerCase())).size") == 13
            assert page.evaluate("JSON.stringify(window.__excelMock.records[0]) === window.__excelMock.original")
            assert len(network["requests"]) == 3, "Inserting an existing capture unexpectedly refetched research"
            checked("six_new_sheets_repeat_insert_no_overwrite_types_and_formula_text")

            page.locator("#currencies").fill("USD")
            assert page.locator("#review").is_hidden() and page.locator("#insert").is_disabled()
            assert page.locator("#preview details").count() == 0 and len(network["requests"]) == 3
            checked("edited_input_invalidates_previous_capture")

            network["mode"] = "partial"
            page.locator("#currencies").fill("USD,EUR")
            page.locator("#refresh").click()
            page.locator("#review").wait_for(state="visible")
            assert "1 request(s) failed" in page.locator("#status").inner_text()
            assert "Funding: 7 rows" in page.locator("#summary").inner_text()
            page.locator("#insert").click()
            page.wait_for_function("window.__excelMock.records.length === 19")
            page.wait_for_function("!document.getElementById('insert').disabled")
            state = page.evaluate("JSON.parse(JSON.stringify(window.__excelMock))")
            status_sheet = next(sheet for sheet in state["records"][-6:] if "Status" in sheet["name"])
            status_values = next(value["values"] for value in status_sheet["ranges"].values() if "values" in value)
            assert sum(row[1] == "failed" for row in status_values[1:]) == 1
            assert sum(row[1] == "returned" for row in status_values[1:]) == 2
            checked("partial_failure_keeps_successes_and_failed_status")

            network["mode"] = "all_failed"
            page.locator("#refresh").click()
            page.wait_for_function("document.getElementById('status').textContent.includes('No requests returned usable research')")
            assert page.locator("#review").is_hidden() and page.locator("#insert").is_disabled()
            assert page.evaluate("window.__excelMock.records.length") == 19
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            page.screenshot(path=str(prefix) + "-all-failed.png", full_page=True)
            checked("all_failed_hides_previous_capture_and_blocks_insertion")

            unsupported = context.new_page()
            unsupported.add_init_script("window.__unsupportedHost=true")
            unsupported.on("pageerror", lambda error: errors.append(str(error)))
            unsupported.goto(local + "/office/excel/taskpane.html?operator=1", wait_until="networkidle")
            unsupported.get_by_text("Open this add-in inside Excel to insert sheets.", exact=False).wait_for()
            assert unsupported.locator("#insert").is_disabled()
            checked("unsupported_host_cannot_insert")

            assert not errors, errors
            assert not network["unexpected"], network["unexpected"]
            for request in network["requests"]:
                assert request["method"] == "GET"
                assert request["headers"].get("x-liquilens-traffic-class") == "synthetic"
                assert request["headers"].get("x-financial-evidence-traffic-class") == "synthetic"
                assert "authorization" not in request["headers"]
            checked("no_uncaught_errors_or_unmocked_external_requests")
            receipt["fixture_api_requests"] = len(network["requests"])
            receipt["created_mock_sheets"] = 18
            receipt["status"] = "PASS"
            context.close()
            browser.close()
            browser = None
    except Exception as error:
        receipt["status"] = "FAIL"
        receipt["error"] = str(error)
        raise
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        receipt["page_errors"] = errors
        receipt["unexpected_network"] = network["unexpected"]
        Path(str(prefix) + ".json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "checks": len(receipt["checks"]),
                      "receipt": str(prefix) + ".json", "native_excel_acceptance": False}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Existing or new evidence directory; contains only this test's output files")
    parser.add_argument("--browser", default="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                        help="Installed Chromium/Chrome executable for a fresh isolated headless profile")
    run(parser.parse_args())
