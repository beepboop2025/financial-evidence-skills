/**
 * Source-linked funding comparison. Change a plain refresh cell to request again.
 * Example: =FINANCIAL_FUNDING(A2:A6,$B$1)
 * @param {Array<Array<string>>|string} currencies Up to five currency codes.
 * @param {string|number|boolean} refreshCell Manually edited dependency, never sent.
 * @return {Array<Array<string|number|boolean>>} Values followed by request status.
 * @customfunction
 */
function FINANCIAL_FUNDING(currencies, refreshCell) {
  return financialOfficeSheet_({currencies: currencies}, "Funding", refreshCell);
}

/**
 * Covered-institution watchlist with gaps and explicitly uncovered selections.
 * Example: =FINANCIAL_WATCHLIST(A2:A6,$B$1)
 * @param {Array<Array<string>>|string} slugs Up to five exact institution slugs.
 * @param {string|number|boolean} refreshCell Manually edited dependency, never sent.
 * @return {Array<Array<string|number|boolean>>} Watchlist, gaps and request status.
 * @customfunction
 */
function FINANCIAL_WATCHLIST(slugs, refreshCell) {
  return financialOfficeSheet_({institutions: slugs}, "Institutions", refreshCell);
}

function financialOfficeSheet_(options, name, refreshCell) {
  if (refreshCell !== undefined && (refreshCell === null || ["string", "number", "boolean"].indexOf(typeof refreshCell) < 0 ||
      (typeof refreshCell === "number" && !Number.isFinite(refreshCell)))) throw new Error("Use one manually edited refresh cell.");
  var requests = OfficeEvidence.plan(options), responses;
  try {
    responses = UrlFetchApp.fetchAll(requests.map(function (r) { return {url: r.url, method: "get", headers: {Accept: "application/json", "X-Liquilens-Client": "google-sheets-office", "X-Financial-Evidence-Traffic-Class": "unverified"}, followRedirects: false, validateHttpsCertificates: true, muteHttpExceptions: true}; }));
  } catch (error) { throw new Error("Public request failed. Retry manually; no old values substituted."); }
  if (responses.length !== requests.length) throw new Error("Incomplete request batch.");
  var results = requests.map(function (request, i) {
    try {
      var response = responses[i], headers = response.getHeaders();
      var type = Object.keys(headers).filter(function (k) { return k.toLowerCase() === "content-type"; }).map(function (k) { return String(headers[k]); })[0] || "";
      if (response.getResponseCode() !== 200 || !/^application\/json(?:\s*;|$)/i.test(type) || response.getContent().length > 4 * 1024 * 1024) throw new Error("Invalid response.");
      return OfficeEvidence.project(request, JSON.parse(response.getContentText()));
    } catch (error) { return OfficeEvidence.failure(request, "Request failed or returned an invalid contract. Retry manually."); }
  });
  var capture = OfficeEvidence.bundle(results), selected = capture.sheets.filter(function (s) { return [name, "Gaps", "Status"].indexOf(s.name) >= 0; });
  var rows = [[OfficeEvidence.NOTE]];
  selected.forEach(function (s) { rows.push([s.name]); rows = rows.concat(s.rows); rows.push([]); });
  var width = Math.max.apply(null, rows.map(function (r) { return r.length; }));
  return rows.map(function (r) { r = r.map(OfficeEvidence.safe); while (r.length < width) r.push(""); return r; });
}
