#!/usr/bin/env python3
"""Ephemeral Linux native-editor acceptance. Never connects to user instances."""
import argparse
import base64
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
            server = ThreadingHTTPServer(("127.0.0.1", 8099), Handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            for suffix, target in (("ods", "xlsx"), ("xlsx", "ods")):
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
                check("onlyoffice_" + suffix + "_native_all_cells", cells=verify(path, expected))
                config = {"document": {"fileType": suffix, "key": secrets.token_hex(16), "title": "Synthetic funding review." + suffix,
                                        "url": f"http://127.0.0.1:8099/review.{suffix}"},
                          "documentType": "cell", "editorConfig": {"mode": "view", "lang": "en"}}
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
                for suffix in ("ods", "xlsx"):
                    page.goto(f"http://127.0.0.1:8099/editor-{suffix}.html")
                    try:
                        page.wait_for_function("window.acceptance.ready || window.acceptance.errors.length", timeout=120000)
                    finally:
                        page.screenshot(path=str(out / ("onlyoffice-" + suffix + ".png")))
                    state = page.evaluate("window.acceptance")
                    assert state == {"ready": True, "errors": []}, state
                    check("onlyoffice_" + suffix + "_browser_document_ready")
                browser.close()
                browser = None
        else:
            start("collabora", ["--cap-add", "MKNOD", "-e", "aliasgroup1=http://127.0.0.1:80", "-e",
                               "extra_params=--o:ssl.enable=false --o:ssl.termination=false --o:net.listen=loopback --o:net.proto=IPv4 --o:net.post_allow.host[0]=127\\.0\\.0\\.1"])
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
                        ws.on("framereceived", lambda payload: events.append(payload) if isinstance(payload, str) and payload.startswith("status:") else None)
                    page.on("websocket", received)
                    page.goto("http://127.0.0.1/index.php/apps/richdocuments/index?fileId=" + ids[suffix])
                    deadline = time.monotonic() + 120
                    while time.monotonic() < deadline and not any("type=spreadsheet" in e for e in events):
                        page.wait_for_timeout(1000)
                    page.screenshot(path=str(out / ("nextcloud-collabora-" + suffix + ".png")))
                    assert any("type=spreadsheet" in e for e in events), "Collabora spreadsheet status was not received through Nextcloud WOPI"
                    check("nextcloud_collabora_" + suffix + "_browser_wopi_loaded", native_status=events[-1][:2000])
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
            subprocess.run(["docker", "rm", "--force", "--volumes", name], capture_output=True, timeout=60)
        # Editor configs contain only ephemeral JWTs; do not publish them in artifacts.
        for path in fixtures.glob("editor-*.html"):
            path.unlink()
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
