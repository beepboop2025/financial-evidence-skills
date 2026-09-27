// Save evidence_job.py's sources.csv locally. Create a blank Power Query,
// paste this function into Advanced Editor and name it SourcesCsv.
// Invoke SourcesCsv("/absolute/path/to/sources.csv") using your local path.
// All cells stay text: source dates and uncertainty labels are not coerced.
let
    SourcesCsv = (Path as text) as table =>
        let
            Raw = Csv.Document(File.Contents(Path), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
            Headers = Table.PromoteHeaders(Raw, [PromoteAllScalars = true]),
            Required = {"topic", "product", "source_url", "retrieved_at", "transport_ok", "source_reported_state", "source_reported_clocks", "source_content_sha256", "evidence_status", "carrier_verification", "error"},
            Missing = List.Difference(Required, Table.ColumnNames(Headers)),
            Checked = if List.Count(Missing) > 0 then error "Expected the workflow capture sources.csv column contract" else Headers,
            Result = Table.TransformColumnTypes(Checked, List.Transform(Table.ColumnNames(Checked), each {_, type text}))
        in
            Result
in
    SourcesCsv
