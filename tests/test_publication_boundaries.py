"""An explicit source publication policy must survive every table projection."""

import copy
import unittest

from test_openbb_tables import MONEY, packet
from financial_evidence.tables import query_packet


class PublicationBoundaryTests(unittest.TestCase):
    def test_raw_benchmark_and_history_respect_rights_at_every_parent(self):
        for state in ("prohibited", "metadata_only", "METADATA-ONLY", "derived_only"):
            for path in ((), ("markets", 0), ("markets", 0, "benchmark")):
                for field in ("redistribution_status", "rights_status"):
                    with self.subTest(state=state, path=path, field=field):
                        doc = copy.deepcopy(MONEY)
                        node = doc
                        for key in path:
                            node = node[key]
                        node[field] = state
                        for dataset in ("money_markets", "money_market_history"):
                            rows = query_packet(
                                packet("money-market", doc), dataset, entity="US-USD"
                            )["results"]
                            self.assertTrue(rows)
                            self.assertTrue(all(row["value"] is None for row in rows))
                            self.assertTrue(
                                all(
                                    row["availability"] == "restricted_or_unavailable"
                                    for row in rows
                                )
                            )

    def test_raw_capital_prices_cannot_be_republished_as_a_derivative(self):
        doc = {
            "schema": "seiche.world-markets.v1",
            "capital_markets": {
                "rights_status": "derived_only",
                "risk_context": {
                    "market_prices": {
                        "vix": {"value": 15},
                        "high_yield_oas": {"value": 3},
                    }
                },
            },
        }
        rows = query_packet(packet("capital-market", doc), "capital_markets")["results"]
        self.assertTrue(all(row["value"] is None for row in rows))

    def test_metadata_only_suppresses_derived_bank_and_liquidity_values(self):
        examples = (
            (
                "bank-risk",
                "bank_risk",
                {"rows": [{"score": 90, "hazard": {"pd_12m": 0.1}}]},
            ),
            (
                "market-liquidity",
                "market_liquidity",
                {"segment_reports": [{"observations": [{"stress_pctl": 0.8}]}]},
            ),
        )
        for topic, dataset, original in examples:
            for state in ("metadata_only", "prohibited"):
                with self.subTest(dataset=dataset, state=state):
                    doc = {**original, "rights_status": state}
                    rows = query_packet(packet(topic, doc), dataset)["results"]
                    self.assertTrue(rows)
                    self.assertTrue(all(row["value"] is None for row in rows))

    def test_derived_only_does_not_suppress_already_published_derived_scores(self):
        doc = {
            "rights_status": "derived_only",
            "rows": [{"score": 0, "hazard": {"pd_12m": 0.01}}],
        }
        rows = query_packet(packet("bank-risk", doc), "bank_risk")["results"]
        self.assertEqual([row["value"] for row in rows], [0, 0.01])


if __name__ == "__main__":
    unittest.main()
