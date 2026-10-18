#!/usr/bin/env python3
"""Ephemeral Linux native-editor acceptance. Never connects to user instances."""
import argparse
import base64
import copy
from datetime import datetime, timezone
import hashlib
import hmac
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import threading
import time
import traceback
import xml.etree.ElementTree as ET

import requests
from playwright.sync_api import sync_playwright

from verify_cells import verify

ROOT = Path(__file__).resolve().parents[2]
IMAGES = json.loads((Path(__file__).with_name("images.json")).read_text())


def command(*args, timeout=600):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"{args[0:2]} exited {result.returncode}: {result.stderr[-4000:]} {result.stdout[-2000:]}")
    return result.stdout.strip()


def wait_http(url, seconds=360, predicate=None):
    print("Waiting for " + url, flush=True)
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            response = requests.get(url, timeout=5)
            if response.ok and (predicate is None or predicate(response)):
                return response
        except requests.RequestException:
            pass
        time.sleep(2)
    raise TimeoutError(f"Service did not become ready: {url}")


def jwt(payload, secret):
    def encode(data):
        return base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).rstrip(b"=")
    content = encode({"alg": "HS256", "typ": "JWT"}) + b"." + encode(payload)
    return (content + b"." + base64.urlsafe_b64encode(hmac.new(secret.encode(), content, hashlib.sha256).digest()).rstrip(b"=")).decode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["onlyoffice", "nextcloud-collabora"])
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    # Host networking is limited to a disposable GitHub-hosted Linux runner.
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted":
        raise SystemExit("Run only in the dedicated GitHub-hosted office-native workflow")
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    fixtures = out / "fixtures"
    command("node", str(ROOT / "scripts/create_office_fixtures.cjs"), str(fixtures))
    expected = json.loads((fixtures / "expected.json").read_text())
    receipt = {"schema": "financial-evidence.office-native.v1", "engine": args.engine,
               "source_commit": command("git", "rev-parse", "HEAD"),
               "observed_at": datetime.now(timezone.utc).isoformat(), "status": "FAIL",
               "scope": "Synthetic native import and editor acceptance; no independent adoption or customer-host certification",
               "checks": [], "images": {}, "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fixtures.iterdir()}}
    names = []
    server = None
    browser = None
    def cancelled(signum, frame):
        raise KeyboardInterrupt("Workflow canceled")
    signal.signal(signal.SIGTERM, cancelled)
    signal.signal(signal.SIGINT, cancelled)
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    def start(kind, extra):
        name = "fe-native-" + kind + "-" + secrets.token_hex(4)
        spec = IMAGES[kind]
        print("Pulling " + kind + " " + spec["image"], flush=True)
        command("docker", "pull", spec["image"], timeout=600)
        print("Starting " + kind, flush=True)
        command("docker", "run", "--detach", "--rm", "--name", name, "--network", "host",
                "--memory", "5g", "--cpus", "2", "--pids-limit", "2048", *extra, spec["image"])
        names.append(name)
        receipt["images"][kind] = {**spec, "runtime_id": command("docker", "inspect", "--format", "{{.Image}}", name)}
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        return name
    def check(name, **extra):
        receipt["checks"].append({"name": name, "status": "PASS", **extra})
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print("PASS " + name, flush=True)
    try:
        if args.engine == "onlyoffice":
            secret = secrets.token_urlsafe(36)
            start("onlyoffice", ["--shm-size", "1g", "-e", "JWT_ENABLED=true", "-e", "JWT_SECRET=" + secret,
                                 "-e", "ALLOW_PRIVATE_IP_ADDRESS=true", "-e", "ALLOW_META_IP_ADDRESS=false"])
            wait_http("http://127.0.0.1/healthcheck")
            class Handler(SimpleHTTPRequestHandler):
                def __init__(self, *a, **kw):
                    super().__init__(*a, directory=str(fixtures), **kw)
                def log_message(self, *a):
                    pass
                def do_POST(self):
                    length = int(self.headers.get("Content-Length", "0"))
                    assert 0 < length < 1024 * 1024
                    data = json.loads(self.rfile.read(length))
                    if data.get("status") in (2, 6):
                        url = data["url"]
                        assert url.startswith("http://127.0.0.1/"), "Save callback escaped the local engine"
                        saved = requests.get(url, timeout=60)
                        saved.raise_for_status()
                        (out / "onlyoffice-saved.xlsx").write_bytes(saved.content)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"error":0}')
            server = ThreadingHTTPServer(("127.0.0.1", 8099), Handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            editor_keys = {}
            for suffix, target in (("xlsx", "ods"), ("ods", "xlsx")):
                key = secrets.token_hex(16)
                payload = {"async": False, "filetype": suffix, "key": key, "outputtype": target,
                           "url": f"http://127.0.0.1:8099/review.{suffix}"}
                response = requests.post("http://127.0.0.1/converter?shardkey=" + key,
                                         json={**payload, "token": jwt(payload, secret)},
                                         headers={"Accept": "application/json"}, timeout=120)
                response.raise_for_status()
                if "json" in response.headers.get("Content-Type", ""):
                    result = response.json()
                    assert not result.get("error"), result
                    converted_url = result["fileUrl"]
                else:
                    xml = ET.fromstring(response.content)
                    assert xml.findtext("Error") is None, response.text[:1000]
                    converted_url = xml.findtext("FileUrl")
                # Converter output must stay on the disposable local service.
                assert converted_url.startswith("http://127.0.0.1/"), converted_url
                converted = requests.get(converted_url, timeout=60)
                converted.raise_for_status()
                path = out / ("onlyoffice-from-" + suffix + "." + target)
                path.write_bytes(converted.content)
                try:
                    cells = verify(path, expected)
                except TypeError as exc:
                    # This known upstream export defect is retained as a failed,
                    # unsupported route. The supported XLSX route stays strict.
                    if suffix != "ods" or "NumberFormatList" not in str(exc) or "formatCode" not in str(exc):
                        raise
                    receipt.setdefault("unsupported_routes", []).append({"route": "onlyoffice_ods_to_xlsx_export", "status": "FAIL",
                        "error": str(exc), "upstream_source": "https://github.com/ONLYOFFICE/core/blob/master/OdfFile/Reader/Converter/xlsx_numFmts.cpp"})
                    print("UNSUPPORTED ONLYOFFICE ODS-to-XLSX export: " + str(exc), flush=True)
                else:
                    check("onlyoffice_" + suffix + "_native_all_cells", cells=cells)
                editor_keys[suffix] = secrets.token_hex(16)
                config = {"document": {"fileType": suffix, "key": editor_keys[suffix], "title": "Synthetic funding review." + suffix,
                                        "url": f"http://127.0.0.1:8099/review.{suffix}"},
                          "documentType": "cell", "editorConfig": {"mode": "edit" if suffix == "xlsx" else "view", "lang": "en",
                              "callbackUrl": "http://127.0.0.1:8099/callback", "user": {"id": "synthetic-office-test", "name": "Synthetic acceptance"}}}
                token = jwt(config, secret)
                html = ('<!doctype html><html><head><title>Financial Evidence acceptance</title></head><body>'
                        '<div id="editor"></div><script src="http://127.0.0.1/web-apps/apps/api/documents/api.js"></script>'
                        '<script>window.acceptance={ready:false,errors:[]};const config=' + json.dumps({**config, "token": token}) + ';'
                        'config.width="100%";config.height="900px";config.events={onDocumentReady:()=>window.acceptance.ready=true,'
                        'onError:e=>window.acceptance.errors.push(e.data)};new DocsAPI.DocEditor("editor",config);</script></body></html>')
                (fixtures / ("editor-" + suffix + ".html")).write_text(html)
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                for suffix in ("xlsx", "ods"):
                    page.goto(f"http://127.0.0.1:8099/editor-{suffix}.html")
                    try:
                        page.wait_for_function("window.acceptance.ready || window.acceptance.errors.length", timeout=120000)
                    finally:
                        page.screenshot(path=str(out / ("onlyoffice-" + suffix + ".png")))
                    state = page.evaluate("window.acceptance")
                    assert state == {"ready": True, "errors": []}, state
                    check("onlyoffice_" + suffix + "_browser_document_ready")
                    if suffix == "xlsx":
                        frame = page.frame_locator("iframe")
                        frame.locator("#ce-cell-name").fill("A1")
                        frame.locator("#ce-cell-name").press("Enter")
                        addition = " - native save verification"
                        marker = expected[0]["rows"][0][0] + addition
                        # Exercise real editor keystrokes: DOM fill() bypasses
                        # ONLYOFFICE's cell model and appends stale cell text.
                        frame.locator("#ce-scroll-content").click()
                        frame.locator("#ce-scroll-content").press("End")
                        frame.locator("#ce-scroll-content").press_sequentially(addition)
                        frame.locator("#ce-scroll-content").press("Enter")
                        saved_path = out / "onlyoffice-saved.xlsx"
                        deadline = time.monotonic() + 60
                        while time.monotonic() < deadline and not saved_path.exists():
                            page.wait_for_timeout(2000)
                            payload = {"c": "forcesave", "key": editor_keys[suffix]}
                            response = requests.post("http://127.0.0.1/command", json={**payload, "token": jwt(payload, secret)}, timeout=10)
                            response.raise_for_status()
                            result = response.json()
                            assert result.get("error") in (0, 4), result
                        assert saved_path.exists(), "Native editor did not save the changed XLSX through its callback"
                        changed = copy.deepcopy(expected)
                        changed[0]["rows"][0][0] = marker
                        check("onlyoffice_xlsx_native_edit_save_all_cells", cells=verify(saved_path, changed))
                browser.close()
                browser = None
        else:
            start("collabora", ["--cap-add", "MKNOD", "-e", "aliasgroup1=http://127.0.0.1:80", "-e",
                               "extra_params=--o:ssl.enable=false --o:ssl.termination=false --o:net.listen=loopback --o:net.proto=IPv4 --o:logging.level=warning --o:net.post_allow.host[0]=127\\.0\\.0\\.1"])
            wait_http("http://127.0.0.1:9980/hosting/discovery")
            for suffix in ("ods", "xlsx"):
                with (fixtures / ("review." + suffix)).open("rb") as file:
                    converted = requests.post("http://127.0.0.1:9980/cool/convert-to/ods",
                                              files={"data": ("review." + suffix, file)}, timeout=120)
                converted.raise_for_status()
                path = out / ("collabora-from-" + suffix + ".ods")
                path.write_bytes(converted.content)
                check("collabora_" + suffix + "_native_all_cells", cells=verify(path, expected))
            password = secrets.token_urlsafe(36)
            nc = start("nextcloud", ["-e", "SQLITE_DATABASE=office-acceptance", "-e", "NEXTCLOUD_ADMIN_USER=office-test",
                                      "-e", "NEXTCLOUD_ADMIN_PASSWORD=" + password, "-e", "NEXTCLOUD_TRUSTED_DOMAINS=127.0.0.1 localhost"])
            wait_http("http://127.0.0.1/status.php", predicate=lambda r: r.json().get("installed") is True)
            def occ(*args):
                return command("docker", "exec", "--user", "www-data", nc, "php", "occ", *args)
            occ("app:disable", "firstrunwizard")
            occ("config:system:set", "allow_local_remote_servers", "--type=boolean", "--value=true")
            # Nextcloud's official release repository supplies the built app;
            # pin the complete bundle instead of floating app-store resolution.
            package = requests.get(IMAGES["nextcloud"]["office_app_url"], timeout=120)
            package.raise_for_status()
            assert hashlib.sha256(package.content).hexdigest() == IMAGES["nextcloud"]["office_app_sha256"]
            archive = out / "richdocuments.tar.gz"
            archive.write_bytes(package.content)
            command("docker", "cp", str(archive), nc + ":/tmp/richdocuments.tar.gz")
            command("docker", "exec", nc, "tar", "-xzf", "/tmp/richdocuments.tar.gz", "-C", "/var/www/html/custom_apps")
            command("docker", "exec", nc, "chown", "-R", "www-data:www-data", "/var/www/html/custom_apps/richdocuments")
            archive.unlink()
            occ("app:enable", "richdocuments")
            version = occ("config:app:get", "richdocuments", "installed_version")
            assert version == IMAGES["nextcloud"]["office_app_version"], ("Review changed Nextcloud Office app before accepting", version)
            for key, value in {"wopi_url": "http://127.0.0.1:9980", "public_wopi_url": "http://127.0.0.1:9980", "wopi_allowlist": "127.0.0.1"}.items():
                occ("config:app:set", "richdocuments", key, "--value=" + value)
            occ("richdocuments:activate-config")
            receipt["nextcloud_office_version"] = version
            session = requests.Session()
            session.auth = ("office-test", password)
            ids = {}
            for suffix in ("ods", "xlsx"):
                source = fixtures / ("review." + suffix)
                url = "http://127.0.0.1/remote.php/dav/files/office-test/" + source.name
                upload = session.put(url, data=source.read_bytes(), timeout=60)
                upload.raise_for_status()
                readback = session.get(url, timeout=60)
                readback.raise_for_status()
                assert readback.content == source.read_bytes()
                properties = session.request("PROPFIND", url, headers={"Depth": "0"},
                    data='<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns"><d:prop><oc:fileid/></d:prop></d:propfind>', timeout=30)
                properties.raise_for_status()
                ids[suffix] = ET.fromstring(properties.content).findtext(".//{http://owncloud.org/ns}fileid")
                assert ids[suffix] and ids[suffix].isdigit()
                check("nextcloud_" + suffix + "_webdav_byte_exact", file_id=ids[suffix])
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page.goto("http://127.0.0.1/login")
                page.locator('input[name="user"]').fill("office-test")
                page.locator('input[name="password"]').fill(password)
                page.locator('button[type="submit"],input[type="submit"]').first.click()
                page.wait_for_url("**/apps/**", timeout=60000)
                for suffix in ("ods", "xlsx"):
                    events = []
                    def received(ws):
                        def message(payload):
                            if isinstance(payload, bytes):
                                payload = payload.decode("utf-8", errors="replace")
                            if payload.startswith("status:"):
                                events.append(payload)
                        ws.on("framereceived", message)
                    page.on("websocket", received)
                    # Use Nextcloud's normal file-opening route; direct access
                    # to richdocuments/index lacks its required CSRF token.
                    page.goto("http://127.0.0.1/index.php/f/" + ids[suffix])
                    deadline = time.monotonic() + 120
                    wanted_tabs = [sheet["name"] for sheet in expected]
                    observed_tabs = []
                    native_frame = None
                    while time.monotonic() < deadline:
                        for frame in page.frames:
                            if ":9980/" in frame.url:
                                observed_tabs = [text.strip() for text in frame.locator(".spreadsheet-tab").all_text_contents()]
                                if observed_tabs == wanted_tabs:
                                    native_frame = frame
                                    break
                        if native_frame:
                            break
                        page.wait_for_timeout(1000)
                    # Close the vendor's first-use tour through its visible UI.
                    for frame in page.frames:
                        close = frame.locator("#welcome-close")
                        if close.count():
                            close.click(timeout=5000)
                    page.screenshot(path=str(out / ("nextcloud-collabora-" + suffix + ".png")))
                    (out / ("nextcloud-collabora-" + suffix + "-visible.txt")).write_text(page.locator("body").inner_text())
                    assert native_frame and observed_tabs == wanted_tabs, ("Native editor did not show every source worksheet", observed_tabs, wanted_tabs)
                    check("nextcloud_collabora_" + suffix + "_browser_wopi_loaded", sheet_tabs=observed_tabs,
                          native_status=events[-1][:2000] if events else "not_exposed_by_cross_frame_browser",
                          editor_url=native_frame.url.split("?")[0])
                    page.remove_listener("websocket", received)
                browser.close()
                browser = None
            session.close()
        receipt["status"] = "PASS"
    except BaseException as exc:
        if isinstance(exc, KeyboardInterrupt):
            receipt["status"] = "CANCELLED"
        receipt["error"] = str(exc)[:5000]
        traceback.print_exc()
        raise
    finally:
        if server:
            server.shutdown()
        # Retain engine logs only from these disposable synthetic instances.
        for name in names:
            result = subprocess.run(["docker", "logs", "--tail", "200", name], capture_output=True, text=True)
            (out / (name + ".log")).write_text((result.stdout + result.stderr)[-100000:])
            if name.startswith("fe-native-nextcloud-"):
                result = subprocess.run(["docker", "exec", name, "tail", "-n", "80", "/var/www/html/data/nextcloud.log"], capture_output=True, text=True)
                (out / "nextcloud-application.log").write_text((result.stdout + result.stderr)[-100000:])
            subprocess.run(["docker", "rm", "--force", "--volumes", name], capture_output=True, timeout=60)
        # Editor configs contain only ephemeral JWTs; do not publish them in artifacts.
        for path in fixtures.glob("editor-*.html"):
            path.unlink()
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
