"""Reacquire all nine values from original publishers; never relabel FRED copies."""

import csv
import hashlib
import io
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser

from .funding_archive import FIELDS, METRICS
from .reliability import NoRedirect, now, strict_json

URLS = {
    "sofr": "https://markets.newyorkfed.org/api/rates/secured/sofr/last/10.json",
    "effr": "https://markets.newyorkfed.org/api/rates/unsecured/effr/last/10.json",
    "iorb": "https://www.federalreserve.gov/releases/prates/data/FRB_PRATES_xml.zip",
    "reserves": "https://www.federalreserve.gov/releases/h41/current/h41.htm",
    "on_rrp": "https://markets.newyorkfed.org/api/rp/reverserepo/all/results/last/10.json",
    "srf": "https://markets.newyorkfed.org/api/rp/repo/all/results/last/20.json",
}
NYFED_TERMS = "https://www.newyorkfed.org/privacy/termsofuse"
BOARD_TERMS = "https://www.federalreserve.gov/disclaimer.htm"
NYFED_NOTICE = (
    "Copyright 2026 Federal Reserve Bank of New York. Content from the New York Fed "
    "subject to the Terms of Use at newyorkfed.org. SOFR, EFFR and operation results "
    "are subject to those Terms of Use. The New York Fed is not responsible for "
    "publication of these data by Liquidity Lab, does not sanction or endorse this "
    "republication, and has no liability for your use. Liquidity Lab is not affiliated "
    "with the New York Fed."
)


def number(value):
    if isinstance(value, bool) or value is None:
        raise ValueError("missing publisher number")
    try:
        result = Decimal(str(value).replace(",", "").strip())
    except InvalidOperation as error:
        raise ValueError("invalid publisher number") from error
    if not result.is_finite():
        raise ValueError("nonfinite publisher number")
    return result


def one(rows):
    if len(rows) != 1:
        raise ValueError("missing or ambiguous publisher observation")
    return rows[0]


def get_source(name, url):
    start = time.monotonic()
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "LiquidityLab-Original-Publisher-Research/1 contact mrinal@liquilens.in",
            "Accept-Encoding": "identity",
        },
    )
    raw = bytearray()
    with urllib.request.build_opener(NoRedirect()).open(
        request, timeout=20
    ) as response:
        if response.status != 200:
            raise ValueError("publisher response unavailable")
        while True:
            if time.monotonic() - start > 30:
                raise TimeoutError("publisher response deadline")
            chunk = response.read1(min(65536, 2000001 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
            if len(raw) > 2000000:
                raise ValueError("publisher response too large")
    return bytes(raw)


class Cells(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.current = None
        self.values = {}

    def handle_starttag(self, tag, attrs):
        if tag == "td":
            self.current = dict(attrs).get("id")
            if self.current:
                if self.current in self.values:
                    raise ValueError("duplicate publisher table cell")
                self.values[self.current] = ""
        if tag == "br" and self.current:
            self.values[self.current] += " "

    def handle_data(self, data):
        if self.current:
            self.values[self.current] += data

    def handle_endtag(self, tag):
        if tag == "td":
            self.current = None


def reserve_observation(raw):
    cells = Cells()
    cells.feed(raw.decode("utf-8"))
    values = {k: " ".join(v.split()) for k, v in cells.values.items()}
    if values.get("t2r16c1") != "Reserve balances with Federal Reserve Banks":
        raise ValueError("H41 reserve row changed")
    header = values.get("t2h2c1", "")
    if not header.startswith("Week ended"):
        raise ValueError("H41 weekly-average column changed")
    observed = (
        datetime.strptime(
            header.removeprefix("Week ended").strip() + " +0000", "%b %d, %Y %z"
        )
        .date()
        .isoformat()
    )
    # WRESBAL's reference is the WEEKLY AVERAGE, not the Wednesday-level column.
    return observed, number(values["t2r16c2"]) / 1000


def iorb_observations(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        member = archive.getinfo("PRATES_data.xml")
        if member.file_size > 2000000:
            raise ValueError("policy-rate XML too large")
        xml = archive.read(member)
    if b"<!DOCTYPE" in xml or b"<!ENTITY" in xml:
        raise ValueError("XML declarations not allowed")
    root = ET.fromstring(xml)
    series = one(
        [
            x
            for x in root.iter()
            if x.tag.endswith("}Series") and x.attrib.get("SERIES_NAME") == "RESBM_N.D"
        ]
    )
    if series.attrib.get("UNIT") != "Percent" or series.attrib.get("UNIT_MULT") != "1":
        raise ValueError("IORB units changed")
    result = {}
    for observation in series:
        if (
            not observation.tag.endswith("}Obs")
            or observation.attrib.get("OBS_STATUS") != "A"
        ):
            continue
        day = date.fromisoformat(observation.attrib["TIME_PERIOD"]).isoformat()
        if day in result:
            raise ValueError("duplicate IORB date")
        result[day] = number(observation.attrib["OBS_VALUE"])
    return result


def operation(raw, day, *, reverse):
    rows = strict_json(raw)["repo"]["operations"]
    kind = "Reverse Repo" if reverse else "Repo"
    matching = [
        x
        for x in rows
        if x.get("operationDate") == day
        and x.get("operationType") == kind
        and x.get("term") == "Overnight"
    ]
    expected_times = {"13:15"} if reverse else {"08:30", "13:45"}
    if (
        len(matching) != len(expected_times)
        or {x.get("closeTime") for x in matching} != expected_times
        or len({x.get("operationId") for x in matching}) != len(matching)
    ):
        raise ValueError("incomplete overnight operation set")
    if any(
        x.get("auctionStatus") != "Results" or x.get("settlementDate") != day
        for x in matching
    ):
        raise ValueError("operation not a settled result")
    amounts = [number(x.get("totalAmtAccepted")) for x in matching]
    if any(x < 0 for x in amounts):
        raise ValueError("negative operation amount")
    latest = max(
        x["operationDate"]
        for x in rows
        if x.get("operationType") == kind and x.get("auctionStatus") == "Results"
    )
    return sum(amounts) / 1000000000, latest


def build(reference, *, getter=get_source):
    rows = reference["results"]
    if tuple(x["metric_id"] for x in rows) != METRICS or any(
        x["value_state"] != "available" for x in rows
    ):
        raise ValueError("nine available reference inputs required")
    targets = {
        r["metric_id"]: date.fromisoformat(r["observation_date"]).isoformat()
        for r in rows
    }
    start = (
        date.fromisoformat(targets["liquidity.tga"]) - timedelta(days=7)
    ).isoformat()
    urls = dict(
        URLS,
        tga="https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance?"
        + urllib.parse.urlencode(
            {
                "filter": "record_date:gte:"
                + start
                + ",account_type:eq:Treasury General Account (TGA) Opening Balance",
                "fields": "record_date,account_type,open_today_bal",
                "sort": "-record_date",
                "page[size]": "100",
            }
        ),
    )

    def acquire(item):
        name, url = item
        raw = getter(name, url)
        return (
            name,
            raw,
            {
                "source_url": url,
                "retrieved_at": now(),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
            },
        )

    with ThreadPoolExecutor(max_workers=3) as pool:
        sources = list(pool.map(acquire, urls.items()))
    raw = {name: data for name, data, _ in sources}
    receipts = {name: receipt for name, _, receipt in sources}
    values = {}
    for kind, metrics in (
        (
            "sofr",
            {
                "policy.sofr": "percentRate",
                "distribution.sofr.p99": "percentPercentile99",
                "distribution.sofr.volume": "volumeInBillions",
            },
        ),
        ("effr", {"policy.effr": "percentRate"}),
    ):
        observations = [
            r
            for r in strict_json(raw[kind])["refRates"]
            if r.get("type") == kind.upper()
        ]
        latest = max(r["effectiveDate"] for r in observations)
        for metric, field in metrics.items():
            observation = one(
                [r for r in observations if r.get("effectiveDate") == targets[metric]]
            )
            values[metric] = (
                number(observation[field]),
                kind,
                "New York Fed Markets API " + kind.upper(),
                latest,
                field,
            )
    iorb = iorb_observations(raw["iorb"])
    values["policy.iorb"] = (
        iorb[targets["policy.iorb"]],
        "iorb",
        "Federal Reserve Board PRATES RESBM_N.D",
        max(iorb),
        "RESBM_N.D/OBS_VALUE",
    )
    reserve_date, reserves = reserve_observation(raw["reserves"])
    if reserve_date != targets["liquidity.reserves"]:
        raise ValueError("H41 weekly-average date does not match the reference")
    values["liquidity.reserves"] = (
        reserves,
        "reserves",
        "Federal Reserve Board H.4.1 weekly average",
        reserve_date,
        "t2r16c2 (millions / 1000)",
    )
    for metric, key, reverse in (
        ("liquidity.on_rrp", "on_rrp", True),
        ("liquidity.srf", "srf", False),
    ):
        value, latest = operation(raw[key], targets[metric], reverse=reverse)
        values[metric] = (
            value,
            key,
            "New York Fed "
            + ("ON RRP" if reverse else "standing repo")
            + " operation results",
            latest,
            "sum(totalAmtAccepted) / 1000000000",
        )
    tga = strict_json(raw["tga"])
    if (
        tga["meta"]["dataFormats"].get("open_today_bal") != "$1,000,000"
        or int(tga["meta"]["total-pages"]) != 1
    ):
        raise ValueError("TGA units or pagination changed")
    candidates = [
        r
        for r in tga["data"]
        if r["account_type"] == "Treasury General Account (TGA) Opening Balance"
    ]
    observed = one(
        [r for r in candidates if r["record_date"] == targets["liquidity.tga"]]
    )
    values["liquidity.tga"] = (
        number(observed["open_today_bal"]) / 1000,
        "tga",
        "US Treasury Daily Treasury Statement opening balance",
        max(r["record_date"] for r in candidates),
        "open_today_bal (millions / 1000)",
    )
    results, assessments, lineage = [], {}, {}
    for row in rows:
        metric = row["metric_id"]
        value, key, source, latest, field = values[metric]
        # Reference UI rounds to two decimals. Never let rounding hide nonzero usage.
        expected = number(row["value"])
        if abs(value - expected) > Decimal("0.005") or (expected == 0 and value != 0):
            raise ValueError("original publisher disagrees with reference: " + metric)
        latest = date.fromisoformat(latest).isoformat()
        newer = latest > targets[metric]
        results.append(
            {
                "metric_id": metric,
                "value": float(value),
                "unit": "%" if metric in METRICS[:4] else "$B",
                "observation_date": targets[metric],
                "source": source,
                "cadence": "weekly" if metric == "liquidity.reserves" else "daily",
                "publisher_freshness": "directly_verified",
                "value_state": "available",
                "evaluated_at": reference["captured_at"],
                "review_status": reference["data_readiness"],
                "review_asof": reference["review_asof"],
                "review_scope": reference["review_scope"],
                "latest_per_instrument": False,
                "canonical_latest_asof": latest,
                "newer_observation_available": newer,
            }
        )
        assessments[metric] = {
            "canonical_latest_asof": latest,
            "newer_observation_available": newer,
            "basis": "Original-publisher observation matches reference within displayed precision; no rounded nonzero accepted as zero.",
        }
        lineage[metric] = {
            **receipts[key],
            "field": field,
            "source": source,
            "original_publisher_acquisition": True,
        }
    review = {
        key: reference[key]
        for key in (
            "capture_id",
            "captured_at",
            "ready",
            "available",
            "stale",
            "review_asof",
            "review_scope",
            "latest_per_instrument",
            "age_seconds",
            "data_readiness",
            "release_identity",
            "runtime_release_identity",
            "observed_release",
            "runtime_release",
            "manifest_sha256",
        )
    }
    review.update(
        schema="financial-evidence.original-publisher-review.v1",
        results=results,
        freshness_assessments=assessments,
        issues=[
            {"code": x["code"], "subject": x["subject"]}
            for x in reference.get("issues", [])
        ],
        original_publisher_acquired_at=now(),
        publisher_lineage=lineage,
        value_basis="independently_retrieved_original_publishers_at_full_source_precision",
        reference_basis="dated_release_and_policy_crosscheck_not_source_of_republished_values",
        method_version="original-publisher-crosscheck.v1",
        publisher_notice=NYFED_NOTICE,
        transformations=[
            "Publisher numbers parsed without rounding",
            "USD millions or dollars converted to USD billions",
            "Morning and afternoon overnight standing-repo results summed",
            "Nine dated inputs joined with independently evaluated review metadata",
        ],
        source_terms={
            "new_york_fed": NYFED_TERMS,
            "federal_reserve_board": BOARD_TERMS,
            "treasury": "https://fiscaldata.treasury.gov/about-us/",
        },
    )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS)
    writer.writeheader()
    for row in results:
        writer.writerow(
            dict(
                row,
                latest_per_instrument="false",
                newer_observation_available=str(
                    row["newer_observation_available"]
                ).lower(),
            )
        )
    return review, stream.getvalue().encode(), sources
