/** @OnlyCurrentDoc */

function onOpen(e) {
  // The no-auth open lifecycle only builds a menu. It reads no cells or data.
  SpreadsheetApp.getUi().createAddonMenu()
    .addItem("Open research review", "showOfficeSidebar").addToUi();
}

function onInstall(e) { onOpen(e); }

function showOfficeSidebar() {
  SpreadsheetApp.getUi().showSidebar(
    HtmlService.createHtmlOutputFromFile("Sidebar").setTitle("Financial Evidence"));
}

function insertOfficeReview(options) {
  options = options || {};
  if (typeof options !== "object" || Array.isArray(options) ||
      Object.keys(options).some(function (key) { return ["currencies", "institutions", "verification"].indexOf(key) < 0; }) ||
      (options.verification !== undefined && typeof options.verification !== "boolean")) {
    throw new Error("Use currencies and exact institution slugs from the review form.");
  }
  var requests = OfficeEvidence.plan({currencies: options.currencies, institutions: options.institutions});
  var lock = LockService.getDocumentLock();
  if (!lock || !lock.tryLock(1000)) throw new Error("A review is already running. Wait for it to finish, then retry.");
  var created = [];
  try {
    var workbook = SpreadsheetApp.getActiveSpreadsheet();
    if (!workbook) throw new Error("Open this add-on from a spreadsheet.");
    var headers = {Accept: "application/json", "X-Liquilens-Client": "google-sheets-addon",
      "X-Financial-Evidence-Traffic-Class": options.verification ? "synthetic" : "unverified"};
    if (options.verification) headers["X-Liquilens-Traffic-Class"] = "synthetic";
    var responses;
    try {
      responses = UrlFetchApp.fetchAll(requests.map(function (request) {
        return {url: request.url, method: "get", headers: headers,
          followRedirects: false, validateHttpsCertificates: true, muteHttpExceptions: true};
      }));
    } catch (error) {
      throw new Error("The public service could not be reached. No review tabs were created. Retry manually.");
    }
    if (responses.length !== requests.length) throw new Error("Incomplete request batch. No review tabs were created.");
    var results = requests.map(function (request, i) {
      try {
        var response = responses[i], receivedHeaders = response.getHeaders();
        var type = Object.keys(receivedHeaders).filter(function (key) { return key.toLowerCase() === "content-type"; })
          .map(function (key) { return String(receivedHeaders[key]); })[0] || "";
        if (response.getResponseCode() !== 200 || !/^application\/json(?:\s*;|$)/i.test(type) ||
            response.getContent().length > 4 * 1024 * 1024) throw new Error("Invalid response.");
        return OfficeEvidence.project(request, JSON.parse(response.getContentText()));
      } catch (error) {
        return OfficeEvidence.failure(request, "Request failed or returned an invalid contract. Retry manually; no old values substituted.");
      }
    });
    var capture = OfficeEvidence.bundle(results), evidence = JSON.stringify(capture, null, 2);
    if (evidence.length > 2 * 1024 * 1024) throw new Error("This capture is too large for the add-on. Narrow the selection or use the browser desk.");
    // Generate and check every tab name before writing. Never find-and-replace a user's tab.
    var stamp = new Date().toISOString().slice(5, 19).replace(/[-:]/g, "").replace("T", "-");
    var prefix = "FE " + stamp + " " + Utilities.getUuid().slice(0, 3);
    var names = capture.sheets.map(function (sheet) { return prefix + " " + sheet.name; });
    if (names.some(function (name) { return workbook.getSheetByName(name) !== null; })) {
      throw new Error("A capture with that name already exists. Retry to create a new capture.");
    }
    capture.sheets.forEach(function (table, index) {
      var sheet = workbook.insertSheet(names[index]);
      created.push(sheet);
      var width = table.rows[0].length;
      var cells = table.rows.map(function (row) { return row.map(OfficeEvidence.safe); });
      var range = sheet.getRange(1, 1, cells.length, width);
      range.setNumberFormats(cells.map(function (row) { return row.map(function (value) { return typeof value === "string" ? "@" : "General"; }); }));
      range.setValues(cells).setVerticalAlignment("top");
      sheet.getRange(1, 1, 1, width).setFontWeight("bold").setBackground("#163f55").setFontColor("#ffffff");
      sheet.setFrozenRows(1).setColumnWidths(1, width, 170);
      if (table.name === "Read me") sheet.setColumnWidth(2, 650).getRange(1, 1, cells.length, width).setWrap(true);
      else if (cells.length > 1) range.createFilter();
    });
    SpreadsheetApp.flush();
    workbook.setActiveSheet(created[0]);
    return {captured_at: capture.captured_at, sheet_names: names,
      failed_requests: results.filter(function (r) { return r.status.request_status === "failed"; }).length,
      request_count: requests.length, evidence_json: evidence};
  } catch (error) {
    // Keep partial new tabs visible for recovery; never delete or overwrite analysis.
    if (created.length) throw new Error("The new capture could not finish. Existing analysis is unchanged. Inspect the " + created.length + " new FE tabs before retrying.");
    throw error;
  } finally { lock.releaseLock(); }
}
