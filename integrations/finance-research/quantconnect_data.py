"""LEAN custom-data candidate for a locally retained forward funding archive.

Copy this file and forward_evidence.py into your own LEAN project, set
ARCHIVE_PATH to your local funding.jsonl, and configure the custom subscription
in UTC with fill_forward=False. This file defines no algorithm or order hooks.
"""
import json

from AlgorithmImports import PythonData, SubscriptionDataSource, SubscriptionTransportMedium
from forward_evidence import MAX_BYTES, numeric_record, utc


class ForwardFundingEvidence(PythonData):
    ARCHIVE_PATH = ""
    # One entity/metric per custom symbol prevents different series sharing values.
    ENTITY_ID = "US-USD"
    METRIC = "SOFR"

    def get_source(self, config, date, is_live_mode):
        if is_live_mode:
            raise ValueError("This example supports retained research files only")
        if not self.ARCHIVE_PATH:
            raise ValueError("Set ARCHIVE_PATH to your reviewed local funding.jsonl")
        return SubscriptionDataSource(self.ARCHIVE_PATH, SubscriptionTransportMedium.LOCAL_FILE)

    def reader(self, config, line, date, is_live_mode):
        if is_live_mode:
            raise ValueError("Live trading integration is not supported")
        if not line.strip():
            return None
        if len(line.encode()) > MAX_BYTES:
            raise ValueError("Funding record exceeds the bounded read size")
        record = numeric_record(json.loads(line))
        row = record["row"]
        if (row["entity_id"], row["metric"]) != (self.ENTITY_ID, self.METRIC):
            return None
        point = ForwardFundingEvidence()
        point.symbol = config.symbol
        # LEAN indexes at end_time. Do not put the old economic date here.
        point.time = utc(record["available_at"]).replace(tzinfo=None)
        point.end_time = point.time
        point.value = row["value"]
        point["event_time"] = record["event_time"]
        point["available_at"] = record["available_at"]
        point["unit"] = row["unit"]
        point["source_url"] = row["source_url"]
        point["source_field"] = row["source_field"]
        point["source_status"] = row.get("source_status")
        point["packet_sha256"] = record["packet_sha256"]
        return point
