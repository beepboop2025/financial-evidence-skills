"""OpenBB Workspace widget definitions and a ready-to-use research app."""

from .tables import DATASETS

SCOPE = """# Financial Evidence Research Desk

Explore Seiche funding benchmarks, LiquiLens covered-bank diagnostics,
Undertow public liquidity observations and Palimpsest publication coverage.

Choose a dataset, filter by entity, and inspect the date, unit and source beside
each value. Money-market history uses its original cadence. Refreshes can reuse
a source response for up to 60 seconds; that never advances its observation date.

Missing and withheld values remain empty. China coverage is metadata only.
Bank diagnostics are corpus monitoring outputs, not credit ratings or validated
forecasts. Liquidity percentiles retain the publisher's replay limitations.
HTTP success describes retrieval, not freshness, usability or investment merit.
Evidence Carrier verification is not performed. Use the source audit and original
documents before making a research claim.

USD Funding Review reads the most recent scheduled capture of nine required
inputs. Its review status includes source disagreements and overdue publication
checks. A stale or failed capture cannot be treated as a passing daily review.
"""


def widgets() -> dict:
    definitions = {
        "evidence_guide": {
            "name": "How to read this desk",
            "description": "Scope, source clocks and research limitations.",
            "type": "markdown",
            "endpoint": "guide",
            "category": "Financial Evidence",
            "source": "Liquidity Lab",
            "gridData": {"w": 40, "h": 5},
        },
    }
    columns = [
        {
            "field": name,
            "headerName": label,
            "cellDataType": kind,
            "chartDataType": "time"
            if name == "as_of"
            else "series"
            if name == "value"
            else "excluded",
        }
        for name, label, kind in (
            ("entity_id", "Entity", "text"),
            ("entity_name", "Name / Measure", "text"),
            ("metric", "Metric", "text"),
            ("value", "Value", "number"),
            ("unit", "Unit", "text"),
            ("as_of", "Observation Date", "dateString"),
            ("availability", "Availability", "text"),
            ("source_status", "Publisher Status", "text"),
            ("rights_status", "Rights Status", "text"),
            ("context", "Scope / Limitations", "text"),
            ("source_url", "Evidence URL", "text"),
            ("source_field", "JSON Pointer", "text"),
            ("retrieved_at", "Retrieved At", "text"),
            ("content_sha256", "Content SHA-256", "text"),
        )
    ]
    for key, dataset in DATASETS.items():
        params = [
            {
                "paramName": "dataset",
                "value": key,
                "label": "Dataset",
                "type": "text",
                "show": False,
            },
            {
                "paramName": "entity",
                "value": "US-USD" if key == "money_market_history" else "",
                "label": "Entity contains",
                "type": "text",
                "description": "Case-insensitive entity ID or name filter.",
            },
            {
                "paramName": "limit",
                "value": 200,
                "label": "Rows (max 2000)",
                "type": "number",
            },
            {
                "paramName": "offset",
                "value": 0,
                "label": "Row offset",
                "type": "number",
            },
        ]
        if key == "money_market_history":
            params.extend(
                [
                    {
                        "paramName": "start_date",
                        "value": "",
                        "label": "From",
                        "type": "date",
                    },
                    {
                        "paramName": "end_date",
                        "value": "",
                        "label": "Through",
                        "type": "date",
                    },
                ]
            )
        definitions[f"evidence_{key}"] = {
            "name": dataset["name"],
            "description": dataset["description"],
            "category": "Financial Evidence",
            "type": "table",
            "endpoint": "api/v1/query",
            "source": "Liquidity Lab",
            "runButton": False,
            "gridData": {"w": 40, "h": 12},
            "params": params,
            "data": {
                "dataKey": "results",
                "table": {
                    "columnsDefs": columns,
                    "showAll": False,
                    "enableCharts": key == "money_market_history",
                    "chartView": {
                        "enabled": key == "money_market_history",
                        "chartType": "line",
                        "cellRangeCols": {"line": ["as_of", "value"]},
                    },
                },
            },
            "mcp_tool": {
                "mcp_server": "Financial Evidence Workspace",
                "tool_id": "financial_evidence_query",
            },
        }
    definitions["evidence_funding_review"] = {
        "name": "USD Funding Review",
        "description": "Nine required observations from one preserved capture, with publication checks and explicit review status.",
        "category": "Financial Evidence",
        "type": "table",
        "endpoint": "api/v1/funding-review",
        "source": "Seiche / Liquidity Lab",
        "params": [],
        "gridData": {"w": 40, "h": 14},
        "data": {
            "dataKey": "results",
            "table": {
                "columnsDefs": [
                    {"field": field, "headerName": label, "cellDataType": kind}
                    for field, label, kind in (
                        ("metric_id", "Observation", "text"),
                        ("value", "Value", "number"),
                        ("unit", "Unit", "text"),
                        ("observation_date", "Observation Date", "dateString"),
                        ("value_state", "Availability", "text"),
                        ("publisher_freshness", "Publisher Freshness", "text"),
                        ("review_status", "Review Status", "text"),
                        ("evaluated_at", "Capture Time", "text"),
                        ("source", "Source", "text"),
                    )
                ]
            },
        },
        "mcp_tool": {
            "mcp_server": "Financial Evidence Workspace",
            "tool_id": "financial_evidence_funding_review",
        },
    }
    return definitions


def apps(base_url: str) -> list[dict]:
    def placement(key, y=0, h=12, params=None):
        return {
            "i": f"evidence_{key}",
            "x": 0,
            "y": y,
            "w": 40,
            "h": h,
            "state": {
                "params": params
                if params is not None
                else {"dataset": key, "entity": "", "limit": 200, "offset": 0}
            },
        }

    return [
        {
            "name": "Financial Evidence Research Desk",
            "description": "Source-cited funding, bank, liquidity and China coverage research from four public projects. No API key required.",
            "img": base_url + "/thumbnail.svg",
            "allowCustomization": True,
            "tabs": {
                "daily_review": {
                    "id": "daily_review",
                    "name": "USD Funding Review",
                    "layout": [
                        placement("guide", 0, 5, {}),
                        placement("funding_review", 5, 14, {}),
                    ],
                },
                "funding": {
                    "id": "funding",
                    "name": "Funding & Capital",
                    "layout": [
                        placement("guide", 0, 5, {}),
                        placement("money_markets", 5),
                        placement("capital_markets", 17),
                    ],
                },
                "history": {
                    "id": "history",
                    "name": "Benchmark History",
                    "layout": [
                        placement(
                            "money_market_history",
                            params={
                                "dataset": "money_market_history",
                                "entity": "US-USD",
                                "limit": 200,
                                "offset": 0,
                            },
                        ),
                    ],
                },
                "banks": {
                    "id": "banks",
                    "name": "Bank Research",
                    "layout": [placement("bank_risk")],
                },
                "liquidity": {
                    "id": "liquidity",
                    "name": "Market Liquidity",
                    "layout": [placement("market_liquidity")],
                },
                "china": {
                    "id": "china",
                    "name": "China Coverage",
                    "layout": [placement("china_economy")],
                },
                "audit": {
                    "id": "audit",
                    "name": "Source Audit",
                    "layout": [placement("source_health")],
                },
            },
            "groups": [],
            "prompts": [
                "Using @[id:evidence_funding_review], report the capture date, review status and each required funding observation. Inspect review issues before relying on the packet; do not treat an older capture as current.",
                "Using @[id:evidence_money_markets], compare published overnight benchmarks with their dates and units. Identify unavailable inputs before drawing conclusions.",
                "Using @[id:evidence_bank_risk], explain the covered-bank diagnostics and their construction-PIT limitations. Do not present them as credit ratings.",
                "Using @[id:evidence_market_liquidity], distinguish visible observations from withheld measures and summarize the validation limits.",
                "Using @[id:evidence_china_economy], explain what is actually published and why missing economic values cannot be treated as zero.",
            ],
            "mcp_servers": [
                {
                    "name": "Financial Evidence Workspace",
                    "url": base_url + "/mcp",
                    "description": "Query the same bounded, cited datasets used by this dashboard.",
                }
            ],
        }
    ]


THUMBNAIL = """<svg xmlns="http://www.w3.org/2000/svg" width="250" height="200" viewBox="0 0 250 200">
<rect width="250" height="200" rx="12" fill="#0e1728"/>
<text x="20" y="39" fill="#5eead4" font-size="12" font-family="sans-serif">LIQUIDITY LAB / OPENBB</text>
<text x="20" y="74" fill="#fff" font-size="22" font-family="sans-serif">Financial Evidence</text>
<text x="20" y="98" fill="#94a3b8" font-size="13" font-family="sans-serif">Four sources. Explicit boundaries.</text>
<path d="M20 148h210M20 174h210" stroke="#334155"/>
<text x="20" y="138" fill="#e2e8f0" font-size="12" font-family="sans-serif">Funding · Banks · Liquidity</text>
<text x="20" y="166" fill="#e2e8f0" font-size="12" font-family="sans-serif">China coverage · Source audit</text></svg>"""
