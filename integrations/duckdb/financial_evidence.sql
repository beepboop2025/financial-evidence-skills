-- Read all four public products from DuckDB without API keys.
-- The signed DuckDB community extension uses GET directly; this matters because
-- dynamic API routes commonly reject the HEAD probe used by file-oriented httpfs.
INSTALL http_request FROM community;
LOAD http_request;

SET http_follow_redirects = false;
SET http_user_agent = 'financial-evidence-duckdb/0.1';

CREATE OR REPLACE MACRO financial_evidence_fetch(
  topic_name,
  product_name,
  source_url
) AS TABLE
SELECT
  topic_name AS topic,
  product_name AS product,
  source_url,
  current_timestamp AS retrieved_at,
  response.status = 200 AS ok,
  response.status AS http_status,
  response.content_type,
  octet_length(response.body) AS bytes,
  CASE
    WHEN response.status = 200
      AND lower(response.content_type) LIKE '%json%'
    THEN try_cast(decode(response.body) AS JSON)
    ELSE NULL
  END AS document
FROM (
  SELECT http_get(
    source_url,
    headers := {'Accept': 'application/json'}
  ) AS response
);

-- Each relation intentionally stays separate: unlike evidence is not blended.
CREATE OR REPLACE VIEW seiche_money_markets AS
SELECT * FROM financial_evidence_fetch(
  'money-market',
  'Seiche',
  'https://api.seiche.info/api/v2/money-markets'
);

CREATE OR REPLACE VIEW seiche_capital_markets AS
SELECT * FROM financial_evidence_fetch(
  'capital-market',
  'Seiche',
  'https://api.seiche.info/api/v2/world-markets?section=capital_markets'
);

CREATE OR REPLACE VIEW seiche_china_macro AS
SELECT * FROM financial_evidence_fetch(
  'china-economy',
  'Seiche',
  'https://api.seiche.info/api/v2/world-markets?section=china_macro'
);

CREATE OR REPLACE VIEW palimpsest_china_revision_state AS
SELECT * FROM financial_evidence_fetch(
  'china-economy',
  'Palimpsest',
  'https://palimpsest.info/readings/china-index-latest.json'
);

CREATE OR REPLACE VIEW liquilens_bank_risk AS
SELECT * FROM financial_evidence_fetch(
  'bank-risk',
  'LiquiLens',
  'https://api.liquilens.in/api/failure-radar/board'
);

CREATE OR REPLACE VIEW undertow_exit_liquidity AS
SELECT * FROM financial_evidence_fetch(
  'market-liquidity',
  'Undertow',
  'https://api.seiche.info/undertow/x402/summary'
);
