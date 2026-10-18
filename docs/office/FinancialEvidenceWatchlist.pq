// Name this query FinancialEvidenceWatchlist. Invoke with {"au-sfb", "bajaj-finance"}.
// Anonymous authentication for https://agents.seiche.info. Manual refresh only.
let
    FinancialEvidenceWatchlist = (Slugs as list) as table =>
        let
            Items = List.Distinct(List.Transform(Slugs, each Text.Trim(_))),
            Valid = List.Count(Items) >= 1 and List.Count(Items) <= 5 and Text.Length(Text.Combine(Items, ",")) <= 160 and
                List.AllTrue(List.Transform(Items, each Text.Length(_) > 0 and Text.Length(_) <= 60 and Text.Select(_, {"a".."z", "0".."9", "-"}) = _ and not Text.StartsWith(_, "-") and not Text.EndsWith(_, "-") and not Text.Contains(_, "--"))),
            Selection = if Valid then Text.Combine(Items, ",") else error "Choose one to five exact institution slugs",
            Raw = Json.Document(Web.Contents("https://agents.seiche.info", [RelativePath = "v1/research/api/v1/workflow", Query = [workflow = "institutions", selection = Selection], Headers = [Accept = "application/json"], Timeout = #duration(0, 0, 0, 30)])),
            Envelope = if Raw[schema] <> "financial-evidence.workflow-result.v1" or Raw[workflow] <> "institutions" or Raw[selection] <> Selection then error "Unexpected watchlist identity" else Raw,
            E = Envelope[evidence],
            Checked = if E[schema] <> "liquilens.institution-monitoring.v1" or E[can_authorize_credit] <> false or E[score_authority] <> false then error "Unexpected evidence authority" else E,
            Missing = List.Transform(Checked[not_covered], each if Value.Is(_, type text) then _ else _[slug]),
            Returned = List.Transform(Checked[rows], each _[slug]) & Missing,
            Complete = if List.Count(Returned) <> List.Count(Items) or List.Count(List.Distinct(Returned)) <> List.Count(Items) or not List.IsEmpty(List.Difference(Items, Returned)) then error "Watchlist omitted or duplicated a selection" else Checked,
            TextJson = (Value as any) as text => Text.FromBinary(Json.FromValue(Value), TextEncoding.Utf8),
            Rows = List.Transform(Complete[rows], (Row) => [slug = Row[slug], name = Row[name], institution_type = Row[institution_type], status = Row[status], latest_period = Row[latest_period], current_metrics = Row[current_metrics], overdue_metrics = Row[overdue_metrics], coverage_complete = Row[coverage_complete], gaps_json = TextJson(Row[gaps]), warnings_json = TextJson(Row[warnings]), categories_json = TextJson(Row[categories]), content_sha256 = Row[content_sha256]]) &
                List.Transform(Missing, each [slug = _, status = "not_covered", coverage_complete = false]),
            Table = Table.FromRecords(Rows, {"slug", "name", "institution_type", "status", "latest_period", "current_metrics", "overdue_metrics", "coverage_complete", "gaps_json", "warnings_json", "categories_json", "content_sha256"}, MissingField.UseNull),
            WithSource = Table.AddColumn(Table, "source_url", each Envelope[source_url], type text),
            WithAsOf = Table.AddColumn(WithSource, "as_of", each Complete[as_of], type text),
            WithRetrieved = Table.AddColumn(WithAsOf, "retrieved_at", each Envelope[retrieved_at], type text),
            WithLimits = Table.AddColumn(WithRetrieved, "limits_json", each TextJson(Complete[limits]), type text),
            Result = Table.AddColumn(WithLimits, "review_url", each "https://api.liquilens.in/api/experimental/v1/banking/monitoring/institutions/" & [slug], type text)
        in Result
in
    FinancialEvidenceWatchlist
