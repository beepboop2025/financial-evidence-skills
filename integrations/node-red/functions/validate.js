// Keep the full table envelope. This is a bounded preview, not a credit or trade decision.
function fail(detail) {
    return [null, {payload: {status: "response_rejected", detail, task: msg.task, financial_authority: "none"}}];
}
if (msg.statusCode !== 200) return fail("Research endpoint returned HTTP " + msg.statusCode + ". No evidence preview was accepted.");
const mime = String((msg.headers || {})["content-type"] || "").split(";")[0].trim().toLowerCase();
if (mime !== "application/json") return fail("Expected JSON; received unexpected content.");
if (typeof msg.payload !== "string" || Buffer.byteLength(msg.payload, "utf8") > 2 * 1024 * 1024) {
    return fail("Response is not text JSON or exceeds the 2 MiB preview check.");
}
let page;
try { page = JSON.parse(msg.payload); } catch (_) { return fail("Response is not valid JSON."); }
function finite(value) {
    if (typeof value === "number") return Number.isFinite(value);
    if (Array.isArray(value)) return value.every(finite);
    if (value && typeof value === "object") return Object.values(value).every(finite);
    return true;
}
if (!finite(page)) return fail("Response contains non-finite numbers.");
const task = msg.task;
if (!task || !page || Array.isArray(page) || page.schema !== "liquidity-lab.openbb-table.v1" || page.dataset !== task.dataset) {
    return fail("Unexpected table schema or dataset identity.");
}
if (page.evidence_status !== "not_evaluated" || page.carrier_verification !== "not_performed" || page.status_semantics !== "transport_only") {
    return fail("Unexpected evidence authority contract.");
}
if (!["complete", "partial", "failed"].includes(page.transport_status)) return fail("Unknown transport state.");
if (!Array.isArray(page.results) || !Number.isInteger(page.total_rows) || page.total_rows < 0 ||
    page.offset !== 0 || page.limit !== task.limit || page.returned_rows !== page.results.length ||
    page.results.length > task.limit || page.total_rows < page.results.length) return fail("Invalid preview pagination.");
const next = page.next_offset;
if (!(next === null ? page.total_rows === page.results.length :
    Number.isInteger(next) && page.results.length > 0 && next === page.results.length && next < page.total_rows)) {
    return fail("Inconsistent pagination; a partial page must not look complete.");
}
const https = value => typeof value === "string" && /^https:\/\/[^/\s]+(?:\/|$)/.test(value);
const digest = value => typeof value === "string" && /^(?:sha256:)?[a-f0-9]{64}$/.test(value);
if (!Array.isArray(page.sources) || !page.sources.length || page.sources.some(source =>
    !source || !https(source.source_url) || !digest(source.content_sha256) || typeof source.retrieved_at !== "string")) {
    return fail("Missing source provenance or content identity.");
}
if (!Array.isArray(page.diagnostics) || typeof page.absence_policy !== "string") return fail("Missing diagnostics or absence policy.");
const metadata = ["entity_id", "entity_name", "metric", "unit", "as_of", "source_status", "availability", "source_field", "observation_url", "retrieved_at", "published_at", "knowledge_time", "rights_status", "context"];
for (const row of page.results) {
    if (!row || row.dataset !== task.dataset || metadata.some(key => !(key in row) || (row[key] !== null && typeof row[key] !== "string")) ||
        !("value" in row) || (row.value !== null && (typeof row.value !== "number" || !Number.isFinite(row.value))) ||
        !https(row.source_url) || !digest(row.content_sha256) ||
        !page.sources.some(source => source.source_url === row.source_url && source.content_sha256 === row.content_sha256) ||
        row.evidence_status !== "not_evaluated" || row.carrier_verification !== "not_performed" || row.financial_authority !== "none") {
        return fail("A row lost its provenance, units, clocks, missingness or authority fields.");
    }
    if (/restricted|withheld|unavailable|missing|refus|failed/i.test(row.availability || "") && row.value !== null) {
        return fail("Unavailable or restricted evidence unexpectedly contains a number.");
    }
}
const sourceStates = page.sources.flatMap(source => ((source.source_reported || {}).state || [])
    .map(state => ({source_url: source.source_url, ...state})));
const sourcePartial = page.sources.some(source => source.ok === false) || sourceStates.some(state => /partial|incomplete|unavailable|failed/i.test(String(state.value)));
const warnings = ["Research preview only: retrieval does not establish freshness, rights, fitness, credit quality or executable liquidity."];
if (page.transport_status !== "complete") warnings.push("Source retrieval is incomplete; review transport_status and diagnostics.");
if (sourcePartial) warnings.push("The source reports partial or unavailable evidence. Read sources[].source_reported alongside each row.");
if (next !== null) warnings.push("More matching rows exist. This is the first page only; narrow the entity or use the bounded Python capture for a full export.");
if (!page.results.length) warnings.push("No matching rows were returned. Missing coverage is not zero risk or calm markets.");
if (page.results.some(row => row.rights_status === null)) warnings.push("Some source-data rights are unspecified; do not infer redistribution permission.");
const preview = {
    schema: "financial-evidence.node-red-preview.v1",
    task, captured_at: new Date().toISOString(),
    pagination_complete: next === null,
    transport_complete: page.transport_status === "complete",
    source_partial_reported: sourcePartial,
    financial_authority: "none",
    warnings,
    table: page
};
return [{payload: preview}, null];
