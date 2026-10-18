/* Office.js adapter. It writes only new sheets; no workbook cells leave Excel. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(require('../office-core.js'));
  else root.OfficeInsert = factory(root.OfficeEvidence);
}(typeof globalThis !== 'undefined' ? globalThis : this, function (E) {
  'use strict';
  function column(n) {
    var value = '';
    while (n) { n--; value = String.fromCharCode(65 + n % 26) + value; n = Math.floor(n / 26); }
    return value;
  }
  function prepare(capture, existing, suffix) {
    if (!capture || capture.schema !== 'financial-evidence.office-capture.v1' ||
        !Array.isArray(capture.sheets) || capture.sheets.length !== 6 ||
        !Array.isArray(capture.requests) || !capture.requests.length) throw new Error('Refresh the research before inserting it.');
    var used = new Set(existing.map(function (name) { return name.toLowerCase(); }));
    var names = ['Read me', 'Funding', 'Institutions', 'Gaps', 'Other data', 'Status'];
    var total = 0;
    var plans = capture.sheets.map(function (sheet, index) {
      if (sheet.name !== names[index] || !Array.isArray(sheet.rows) || !sheet.rows.length || sheet.rows.length > 1000) throw new Error('Unexpected review table.');
      var width = sheet.rows[0].length;
      if (!width || width > 25 || sheet.rows.some(function (row) { return !Array.isArray(row) || row.length !== width; })) throw new Error('Unexpected review columns.');
      total += sheet.rows.length * width;
      var stem = 'FE ' + String(suffix).replace(/[^0-9]/g, '').slice(-10) + ' ' + sheet.name;
      var name = stem.slice(0,31), counter = 1;
      while (used.has(name.toLowerCase())) { counter++; var tail = ' ' + counter; name = stem.slice(0, 31-tail.length) + tail; }
      used.add(name.toLowerCase());
      var values = sheet.rows.map(function (row) { return row.map(E.safe); });
      var formats = sheet.rows.map(function (row) { return row.map(function (v) { return typeof v === 'string' ? '@' : 'General'; }); });
      return {name: name, values: values, formats: formats, address: 'A1:' + column(width) + values.length,
        header: 'A1:' + column(width) + '1', source: sheet.name};
    });
    if (total > 20000 || new TextEncoder().encode(JSON.stringify(plans)).byteLength > 2 * 1024 * 1024) throw new Error('This review is too large to insert safely. Download the workbook from the office desk instead.');
    return plans;
  }
  async function insert(capture, Excel, suffix) {
    var created = [];
    try {
      return await Excel.run(async function (context) {
        var sheets = context.workbook.worksheets;
        sheets.load('items/name');
        await context.sync();
        var plans = prepare(capture, sheets.items.map(function (s) { return s.name; }), suffix);
        for (var plan of plans) {
          var sheet = sheets.add(plan.name);
          created.push(plan.name);
          var range = sheet.getRange(plan.address);
          range.numberFormat = plan.formats;
          range.values = plan.values;
          range.format.columnWidth = 140;
          range.format.rowHeight = 20;
          var header = sheet.getRange(plan.header);
          header.format.fill.color = '#164E63';
          header.format.font.color = '#FFFFFF';
          header.format.font.bold = true;
          if (plan.source === 'Read me') {
            sheet.getRange('B1:B4').format.columnWidth = 440;
            sheet.getRange('B2:B4').format.wrapText = true;
            sheet.getRange('B2:B4').format.rowHeight = 80;
          }
        }
        await context.sync();
        return plans.map(function (p) { return p.name; });
      });
    } catch (error) {
      // A failed Office batch can leave partial new sheets. Never remove or
      // overwrite anything automatically, including another user's work.
      if (created.length) throw new Error('Excel could not finish inserting this review. Inspect the new FE sheets before retrying; some may be incomplete. Existing sheets were not overwritten.');
      throw error;
    }
  }
  return {prepare: prepare, insert: insert};
}));
