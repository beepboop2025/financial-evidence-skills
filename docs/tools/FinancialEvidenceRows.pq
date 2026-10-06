// Excel / Power BI: create a blank query, paste into Advanced Editor,
// name it FinancialEvidenceRows, then invoke e.g. FinancialEvidenceRows("money_markets").
// Use Anonymous authentication for https://api.seiche.info; no key is needed.
let
    FinancialEvidenceRows = (Dataset as text, optional Entity as nullable text) as table =>
        let
            Supported = {"money_markets", "money_market_history", "capital_markets", "bank_risk", "market_liquidity", "china_economy", "source_health"},
            CheckedDataset = if List.Contains(Supported, Dataset) then Dataset else error "Unsupported dataset",
            EntityFilter = if Entity = null then "" else Entity,
            Raw = Web.Contents("https://api.seiche.info", [
                RelativePath = "openbb/api/v1/query",
                Query = [dataset = CheckedDataset, entity = EntityFilter, limit = "2000", offset = "0"],
                Headers = [Accept = "application/json"],
                Timeout = #duration(0, 0, 0, 30)
            ]),
            Document = Json.Document(Raw),
            Checked =
                if Document[schema] <> "liquidity-lab.openbb-table.v1" or Document[dataset] <> Dataset then error "Unexpected dataset contract"
                else if Document[transport_status] <> "complete" then error "Source retrieval incomplete: inspect https://api.seiche.info/openbb/api/v1/sources"
                else if Document[evidence_status] <> "not_evaluated" or Document[carrier_verification] <> "not_performed" then error "Unexpected evidence authority contract"
                else if Document[next_offset] <> null then error "More than 2000 rows: narrow Entity or use research_client.py for complete paginated captures"
                else if Document[returned_rows] <> List.Count(Document[results]) or Document[total_rows] <> Document[returned_rows] then error "Incomplete table"
                else Document,
            Columns = {"dataset", "product", "entity_id", "entity_name", "metric", "value", "unit", "as_of", "availability", "source_status", "source_url", "source_field", "observation_url", "retrieved_at", "content_sha256", "published_at", "knowledge_time", "rights_status", "context", "transport_status", "evidence_status", "financial_authority", "carrier_verification"},
            Rows = Table.FromRecords(Checked[results], Columns, MissingField.UseNull),
            Typed = Table.TransformColumnTypes(Rows, List.Transform(Columns, each {_, if _ = "value" then type number else type text}))
        in
            Typed
in
    FinancialEvidenceRows
