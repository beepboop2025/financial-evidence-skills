// One user click makes one bounded GET to the fixed public research endpoint.
function fail(detail) {
    return [null, {payload: {status: "request_rejected", detail, financial_authority: "none"}}];
}
const task = msg.payload;
const datasets = ["money_markets", "bank_risk", "market_liquidity"];
if (!task || typeof task !== "object" || Array.isArray(task)) return fail("Choose a research task object.");
if (Object.keys(task).some(key => !["dataset", "entity", "limit", "synthetic"].includes(key))) {
    return fail("Supported task fields: dataset, entity, limit and synthetic.");
}
if (!datasets.includes(task.dataset)) return fail("Choose money_markets, bank_risk or market_liquidity.");
if (typeof task.entity !== "string" || task.entity.length > 100) return fail("Entity must be a string of at most 100 characters.");
if (!Number.isInteger(task.limit) || task.limit < 1 || task.limit > 200) return fail("Limit must be an integer from 1 to 200.");
if (typeof task.synthetic !== "boolean") return fail("Synthetic must be true for operator tests, false for your own research.");
const query = "dataset=" + encodeURIComponent(task.dataset) + "&entity=" + encodeURIComponent(task.entity) + "&limit=" + task.limit + "&offset=0";
// Build a fresh message so upstream URL/header/payload properties cannot leak into HTTP.
const request = {
    _msgid: msg._msgid,
    task: {...task},
    method: "GET",
    url: "https://agents.seiche.info/v1/research/api/v1/query?" + query,
    headers: {Accept: "application/json", "User-Agent": "Financial-Evidence-Node-RED/1.0"},
    requestTimeout: 20000,
    followRedirects: false
};
if (task.synthetic) {
    request.headers["X-Liquilens-Traffic-Class"] = "synthetic";
    request.headers["X-Financial-Evidence-Traffic-Class"] = "synthetic";
    request.headers["User-Agent"] = "Financial-Evidence-Operator-Verification/1.0";
}
return [request, null];
