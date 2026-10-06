#!/usr/bin/env python3
"""Exercise OpenBB's generated interface against controlled source fixtures."""
import json
from importlib.metadata import version
from pathlib import Path
import sys
from unittest.mock import patch

from openbb import obb
from financial_evidence.tables import query_packet

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from test_openbb_tables import packet


def verify():
    assert len(obb.financial_evidence.datasets().to_df()) == 7
    expected = query_packet(packet("money-market"), "money_markets")
    with patch("financial_evidence.openbb_router._service") as service:
        service.return_value.query.return_value = expected
        result = obb.financial_evidence.query(dataset="money_markets")
        service.return_value.query.assert_called_once_with(
            "money_markets", entity=None, start_date=None, end_date=None, limit=200, offset=0,
        )
    frame = result.to_df()
    assert len(frame) == 2
    assert frame.iloc[0]["value"] == 0
    assert frame["value"].isna().tolist() == [False, True]
    assert frame.iloc[0]["as_of"] == "2026-09-24"
    assert frame.iloc[0]["published_at"] == "2026-09-25"
    assert frame.iloc[0]["knowledge_time"] == "2026-09-26"
    assert frame.iloc[1]["availability"] == "restricted_or_unavailable"
    assert result.extra["financial_evidence"]["sources"] == expected["sources"]
    assert result.extra["financial_evidence"]["evidence_status"] == "not_evaluated"
    assert callable(obb.financial_evidence.sources)
    return {"openbb_core": version("openbb-core"), "status": "passed",
            "generated_query_rows": len(frame), "network_used": False,
            "zero_null_dates_and_provenance_preserved": True}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
