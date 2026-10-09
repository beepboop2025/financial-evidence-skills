"""One bounded synthetic public query through a serialized native pipeline."""

import json
from haystack import Pipeline
from financial_evidence_haystack import FinancialEvidenceQuery

pipeline = Pipeline()
pipeline.add_component("funding", FinancialEvidenceQuery(synthetic=True))
restored = Pipeline.loads(
    pipeline.dumps(), allowed_modules=["financial_evidence_haystack.query"]
)
result = restored.run({"funding": {"dataset": "money_markets", "entity": "USD", "limit": 3}})
evidence = result["funding"]["evidence"]
assert evidence["financial_authority"] == "none"
assert evidence["evidence_status"] == "not_evaluated"
assert evidence["carrier_verification"] == "not_performed"
assert evidence["returned_rows"] <= 3
print(json.dumps(evidence, indent=2, allow_nan=False))
