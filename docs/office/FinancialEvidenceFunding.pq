// First install FinancialEvidenceRows from ../tools/FinancialEvidenceRows.pq.
// Name this query FinancialEvidenceFunding. Invoke with {"USD", "EUR", "INR"}.
// Anonymous access; manually refresh in an Excel/Power BI edition with Web support.
let
    FinancialEvidenceFunding = (Currencies as list) as table =>
        let
            Codes = List.Distinct(List.Transform(Currencies, each Text.Upper(Text.Trim(_)))),
            Checked = if List.Count(Codes) < 1 or List.Count(Codes) > 5 or
                List.AnyTrue(List.Transform(Codes, each Text.Length(_) <> 3 or Text.Select(_, {"A".."Z"}) <> _))
                then error "Choose one to five three-letter currencies" else Codes,
            Tables = List.Transform(Checked, (Currency) =>
                let
                    Raw = FinancialEvidenceRows("money_markets", Currency),
                    Nonempty = if Table.IsEmpty(Raw) then error ("No covered rows for " & Currency) else Raw,
                    Denied = {"restricted", "withheld", "unavailable", "not_available", "denied", "pending", "review_required", "prohibited", "metadata_only", "derived_only"},
                    Safe = Table.FromRecords(List.Transform(Table.ToRecords(Nonempty), (Row) =>
                        let
                            States = List.Transform({Row[availability], Row[source_status], Row[rights_status]}, each Text.Replace(Text.Replace(Text.Lower(if _ = null then "" else _), "-", "_"), " ", "_")),
                            Blocked = List.AnyTrue(List.Transform(States, (State) => List.AnyTrue(List.Transform(Denied, each Text.Contains(State, _))))),
                            Value = if Blocked then null else Row[value]
                        in Record.AddField(Record.TransformFields(Row, {{"value", each Value}}), "value_state", if Blocked and Row[value] <> null then "withheld_by_client" else if Value = null then "null" else "number"))),
                    Selected = Table.AddColumn(Safe, "selection", each Currency, type text)
                in Selected),
            Result = Table.Combine(Tables)
        in Result
in
    FinancialEvidenceFunding
