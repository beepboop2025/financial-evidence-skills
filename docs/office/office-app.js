(function () {
  "use strict";
  var E = OfficeEvidence, W = OfficeWorkbook, $ = function (id) { return document.getElementById(id); };
  var verification = new URLSearchParams(location.search).get("operator") === "1";
  function node(tag, text) { var n = document.createElement(tag); n.textContent = text; return n; }
  function download(data, name, type) {
    var url = URL.createObjectURL(new Blob([data], {type: type})), link = document.createElement("a");
    link.href = url; link.download = name; document.body.append(link); link.click(); link.remove(); setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }
  function button(parent, label, name, type, data) {
    var b = node("button", label); b.type = "button"; b.className = "button";
    b.addEventListener("click", function () {
      try { download(data(), name, type); } catch (error) { $("status").textContent = "Export failed: " + error.message; $("status").classList.add("error"); }
    }); parent.append(b);
  }
  function render(capture) {
    $("scope").textContent = capture.scope; $("capture-time").textContent = "Retrieved " + capture.captured_at + ". Inspect individual source dates before comparing rows.";
    $("downloads").replaceChildren(); $("csv-downloads").replaceChildren(); $("previews").replaceChildren();
    button($("downloads"), "Excel workbook", "review.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", function () { return W.xlsx(capture); });
    button($("downloads"), "LibreOffice workbook", "review.ods", "application/vnd.oasis.opendocument.spreadsheet", function () { return W.ods(capture); });
    button($("downloads"), "Document brief", "brief.html", "text/html;charset=utf-8", function () { return E.html(capture); });
    button($("downloads"), "Full evidence JSON", "evidence.json", "application/json", function () { return JSON.stringify(capture, null, 2) + "\n"; });
    capture.sheets.forEach(function (sheet) {
      button($("csv-downloads"), sheet.name + " CSV", sheet.name.toLowerCase().replaceAll(" ", "-") + ".csv", "text/csv;charset=utf-8", function () { return E.csv(sheet.rows); });
      if (sheet.name === "Read me" || sheet.rows.length < 2) return;
      var details = document.createElement("details"), count = sheet.rows.length - 1;
      details.open = ["Funding", "Institutions", "Status"].indexOf(sheet.name) >= 0;
      details.append(node("summary", sheet.name + " · " + count + " rows"));
      if (count > 20) details.append(node("p", "Previewing 20 rows. Download the workbook or CSV for all " + count + " returned rows."));
      var wrap = document.createElement("div"), table = document.createElement("table"); wrap.className = "table-wrap"; wrap.tabIndex = 0;
      wrap.setAttribute("role", "region"); wrap.setAttribute("aria-label", sheet.name + " preview");
      var head = document.createElement("thead"), body = document.createElement("tbody");
      sheet.rows.slice(0, 21).forEach(function (row, i) {
        var tr = document.createElement("tr"); row.forEach(function (v) { var c = node(i === 0 ? "th" : "td", v); if (i === 0) c.scope = "col"; tr.append(c); }); (i === 0 ? head : body).append(tr);
      }); table.append(head, body); wrap.append(table); details.append(wrap); $("previews").append(details);
    });
    $("results").hidden = false; $("result-title").focus({preventScroll: true});
  }
  $("office-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    var options = {currencies: $("currencies").value, institutions: $("institutions").value,
      datasets: Array.from(document.querySelectorAll('input[name="dataset"]:checked')).map(function (e) { return e.value; }), verification: verification};
    // Invalidate old downloads before validation or a new network request.
    $("results").hidden = true; $("downloads").replaceChildren(); $("csv-downloads").replaceChildren(); $("status").classList.remove("error");
    var controls = Array.from($("office-form").querySelectorAll("input,button"));
    try {
      E.plan(options); controls.forEach(function (c) { c.disabled = true; }); $("status").textContent = "Retrieving selected research. Sources may take up to 30 seconds per request; each outcome stays visible.";
      var capture = await E.run(options), failed = capture.requests.filter(function (r) { return r.status.request_status === "failed"; }).length;
      render(capture); $("status").textContent = (failed ? failed + " of " + capture.requests.length + " requests failed. Check Status before using the remaining rows." : "Research returned. Check source dates, coverage and gaps before using the files.");
      if (failed) $("status").classList.add("error");
    } catch (error) { $("status").textContent = error.message; $("status").classList.add("error"); }
    finally { controls.forEach(function (c) { c.disabled = false; }); }
  });
}());
