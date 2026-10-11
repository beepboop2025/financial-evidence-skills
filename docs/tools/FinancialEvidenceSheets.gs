/**
 * Returns one page of source-linked research plus visible retrieval metadata.
 * Example: =FINANCIAL_EVIDENCE("money_markets","",50,0,$B$1)
 *
 * @param {string} dataset Dataset name; default money_markets.
 * @param {string} entity Optional entity ID/name substring, at most 100 characters.
 * @param {number} limit Rows in this page, 1..200; default 50.
 * @param {number} offset Starting row, 0..100000; default 0.
 * @param {number|string|boolean} refreshCell Optional manually changed cell value.
 * @return {Array<Array<string|number|boolean>>} Status rows, headers and evidence rows.
 * @customfunction
 */
function FINANCIAL_EVIDENCE(dataset, entity, limit, offset, refreshCell) {
  var request = financialEvidenceRequest_(dataset, entity, limit, offset, refreshCell);
  var response;
  try {
    // One fixed public endpoint. No spreadsheet reads, credentials or retries.
    response = UrlFetchApp.fetch(request.url, {
      method: "get",
      headers: { Accept: "application/json", "X-Liquilens-Client": "google-sheets" },
      followRedirects: false,
      validateHttpsCertificates: true,
      muteHttpExceptions: true
    });
  } catch (error) {
    throw new Error("Public research request failed. Retry manually; no data was substituted.");
  }
  var code = response.getResponseCode();
  if (code !== 200) {
    throw new Error("Research HTTP " + code + ". Redirects and automatic retries are disabled.");
  }
  var headers = response.getHeaders();
  var type = Object.keys(headers).filter(function (key) {
    return key.toLowerCase() === "content-type";
  }).map(function (key) { return String(headers[key]); })[0] || "";
  if (!/^application\/json(?:\s*;|$)/i.test(type)) {
    throw new Error("Expected research JSON; received another content type.");
  }
  if (response.getContent().length > 4 * 1024 * 1024) {
    throw new Error("Response exceeds the 4 MiB limit. Narrow the query.");
  }
  var page;
  try {
    page = JSON.parse(response.getContentText());
  } catch (error) {
    throw new Error("Invalid research JSON; no data was substituted.");
  }
  return financialEvidenceTable_(page, request, new Date().toISOString());
}

function financialEvidenceRequest_(dataset, entity, limit, offset, refreshCell) {
  var supported = ["money_markets", "money_market_history", "capital_markets", "bank_risk",
    "market_liquidity", "china_economy", "source_health"];
  dataset = dataset === undefined || dataset === "" ? "money_markets" : dataset;
  entity = entity === undefined ? "" : entity;
  limit = limit === undefined || limit === "" ? 50 : limit;
  offset = offset === undefined || offset === "" ? 0 : offset;
  if (typeof dataset !== "string" || supported.indexOf(dataset) === -1) {
    throw new Error("Choose a supported Financial Evidence dataset.");
  }
  if (typeof entity !== "string" || entity.length > 100) {
    throw new Error("Entity must be one text value of at most 100 characters.");
  }
  if (!Number.isInteger(limit) || limit < 1 || limit > 200 ||
      !Number.isInteger(offset) || offset < 0 || offset > 100000) {
    throw new Error("Use integer limit 1..200 and offset 0..100000.");
  }
  if (refreshCell !== undefined &&
      (refreshCell === null || ["number", "string", "boolean"].indexOf(typeof refreshCell) === -1 ||
       (typeof refreshCell === "number" && !Number.isFinite(refreshCell)))) {
    throw new Error("Refresh must reference one manually edited text, number or checkbox cell.");
  }
  // refreshCell is a Sheets recalculation dependency; its value is never sent.
  return {
    dataset: dataset, limit: limit, offset: offset,
    url: "https://api.seiche.info/openbb/api/v1/query?dataset=" + encodeURIComponent(dataset) +
      "&entity=" + encodeURIComponent(entity) + "&limit=" + limit + "&offset=" + offset
  };
}

function financialEvidenceTable_(page, request, fetchedAt) {
  if (!page || page.schema !== "liquidity-lab.openbb-table.v1" || page.dataset !== request.dataset ||
      ["complete", "partial", "unavailable"].indexOf(page.transport_status) === -1 ||
      page.status_semantics !== "transport_only" || page.evidence_status !== "not_evaluated" ||
      page.carrier_verification !== "not_performed") {
    throw new Error("Unexpected table or evidence authority contract.");
  }
  var rows = page.results;
  if (!Array.isArray(rows) || !Number.isInteger(page.total_rows) || page.total_rows < 0 ||
      page.offset !== request.offset || page.limit !== request.limit ||
      page.returned_rows !== rows.length || rows.length > request.limit ||
      rows.length !== Math.min(request.limit, Math.max(0, page.total_rows - request.offset)) ||
      page.next_offset !== (request.offset + request.limit < page.total_rows ? request.offset + request.limit : null)) {
    throw new Error("Invalid page bounds or counts; no partial page was disguised as complete.");
  }
  if (!Array.isArray(page.sources) || page.sources.length === 0 ||
      page.sources.some(function (source) {
        return !source || typeof source.source_url !== "string" || !/^https:\/\//.test(source.source_url) ||
          (source.ok === true && !/^(sha256:)?[a-f0-9]{64}$/.test(source.content_sha256 || ""));
      }) || !Array.isArray(page.diagnostics)) {
    throw new Error("Missing source provenance or diagnostics.");
  }
  var columns = ["dataset", "product", "entity_id", "entity_name", "metric", "value", "value_state",
    "unit", "as_of", "availability", "source_status", "source_url", "source_field", "observation_url",
    "retrieved_at", "content_sha256", "published_at", "knowledge_time", "rights_status", "context",
    "transport_status", "evidence_status", "financial_authority", "carrier_verification"];
  var withheld = 0;
  var rendered = rows.map(function (row) {
    if (!row || row.dataset !== request.dataset || !Object.prototype.hasOwnProperty.call(row, "value") ||
        (row.value !== null && (typeof row.value !== "number" || !Number.isFinite(row.value))) ||
        row.evidence_status !== "not_evaluated" || row.financial_authority !== "none" ||
        row.carrier_verification !== "not_performed" ||
        ["complete", "partial", "unavailable"].indexOf(row.transport_status) === -1) {
      throw new Error("Unexpected row identity, numeric value or authority fields.");
    }
    var blocked = financialEvidenceBlocked_(row);
    if (blocked && row.value !== null) withheld += 1;
    return columns.map(function (key) {
      if (key === "value") return row.value === null || blocked ? "" : row.value;
      if (key === "value_state") return blocked && row.value !== null ? "withheld_by_client" : row.value === null ? "null" : "number";
      return financialEvidenceCell_(row[key]);
    });
  });
  var allRows = request.offset === 0 && page.next_offset === null;
  var metadata = [
    ["FINANCIAL_EVIDENCE", request.dataset + " — one request; research use"],
    ["transport_status", page.transport_status + " (retrieval only; inspect source states below)"],
    ["page_scope", allRows ? "all_matching_rows_in_this_response" : "partial_dataset_page"],
    ["page_counts", "offset=" + page.offset + "; returned=" + rows.length + "; total=" + page.total_rows + "; limit=" + page.limit],
    ["next_offset", page.next_offset === null ? "none" : page.next_offset],
    ["evidence_status", page.evidence_status],
    ["carrier_verification", page.carrier_verification],
    ["financial_authority", "none"],
    ["source_provenance_json", JSON.stringify(page.sources)],
    ["diagnostics_json", JSON.stringify(page.diagnostics)],
    ["fetched_at_utc", fetchedAt],
    ["client_withheld_numeric_rows", withheld],
    ["interpretation", "Blank numeric cells are missing or withheld, never zero. Rights unknown is not permission. Source timestamps are not refresh time."]
  ].map(function (row) {
    var result = row.map(financialEvidenceCell_);
    while (result.length < columns.length) result.push("");
    return result;
  });
  return metadata.concat([columns], rendered);
}

function financialEvidenceBlocked_(row) {
  var denied = ["restricted", "withheld", "unavailable", "not_available", "denied", "pending",
    "review_required", "prohibited", "metadata_only", "derived_only"];
  return row.publication_allowed === false || [row.availability, row.source_status, row.rights_status].some(function (state) {
    var normal = state === null || state === undefined ? "" : String(state).toLowerCase().replace(/[ -]/g, "_");
    return denied.some(function (word) { return normal.indexOf(word) !== -1; });
  });
}

function financialEvidenceCell_(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "boolean") return value;
  if (typeof value !== "string") throw new Error("Unexpected structured table cell.");
  if (value.length > 45000) throw new Error("A provenance cell is too large for this Sheets view; use the research client.");
  // Protect against formulas in untrusted source text, including copied CSV.
  return /^[\t\r\n]/.test(value) || /^[\s]*[=+\-@]/.test(value) ? "'" + value : value;
}
