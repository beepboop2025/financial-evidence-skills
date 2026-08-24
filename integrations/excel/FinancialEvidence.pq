// Paste this query into Excel Power Query's Advanced Editor.
// Invoke FinancialEvidence("money-market") or any key in Routes below.
let
    Routes = [
        #"money-market" = [
            Product = "Seiche",
            Base = "https://api.seiche.info",
            Path = "api/v2/money-markets",
            Query = []
        ],
        #"capital-market" = [
            Product = "Seiche",
            Base = "https://api.seiche.info",
            Path = "api/v2/world-markets",
            Query = [section = "capital_markets"]
        ],
        #"china-economy" = [
            Product = "Palimpsest",
            Base = "https://palimpsest.info",
            Path = "readings/china-index-latest.json",
            Query = []
        ],
        #"bank-risk" = [
            Product = "LiquiLens",
            Base = "https://api.liquilens.in",
            Path = "api/failure-radar/board",
            Query = []
        ],
        #"market-liquidity" = [
            Product = "Undertow",
            Base = "https://api.seiche.info",
            Path = "undertow/x402/summary",
            Query = []
        ]
    ],
    FinancialEvidence = (Topic as text) as table =>
        let
            Route = Record.Field(Routes, Topic),
            Options = [
                RelativePath = Route[Path],
                Query = Route[Query],
                Headers = [Accept = "application/json"]
            ],
            Raw = Binary.Buffer(Web.Contents(Route[Base], Options)),
            Document = Json.Document(Raw),
            RetrievedAt = DateTimeZone.FixedUtcNow(),
            SourceUrl =
                Route[Base] & "/" & Route[Path] &
                (if Record.FieldCount(Route[Query]) = 0 then "" else
                    "?" & Uri.BuildQueryString(Route[Query])),
            Result = #table(
                {"topic", "product", "source_url", "retrieved_at", "document"},
                {{Topic, Route[Product], SourceUrl, RetrievedAt, Document}}
            )
        in
            Result
in
    FinancialEvidence

