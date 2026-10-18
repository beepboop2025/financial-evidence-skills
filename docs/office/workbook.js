/* Small, macro-free ODS and XLSX writers. Text cells never become formulas. */
var OfficeWorkbook = (function () {
  "use strict";
  var E = typeof OfficeEvidence !== "undefined" ? OfficeEvidence : require("./office-core.js");
  var x = E.xml;
  function utf8(text) { return new TextEncoder().encode(text); }
  function crc32(bytes) {
    var crc = 0xFFFFFFFF;
    for (var i = 0; i < bytes.length; i++) {
      crc ^= bytes[i];
      for (var j = 0; j < 8; j++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xEDB88320 : 0);
    }
    return (crc ^ 0xFFFFFFFF) >>> 0;
  }
  function concat(parts) {
    var result = new Uint8Array(parts.reduce(function (n, p) { return n + p.length; }, 0)), offset = 0;
    parts.forEach(function (p) { result.set(p, offset); offset += p.length; }); return result;
  }
  function zip(entries) {
    var local = [], central = [], offset = 0;
    Object.keys(entries).forEach(function (name) {
      var path = utf8(name), data = utf8(entries[name]), crc = crc32(data), h = new Uint8Array(30), d = new DataView(h.buffer);
      d.setUint32(0, 0x04034B50, true); d.setUint16(4, 20, true); d.setUint16(6, 0x800, true); d.setUint16(12, 0x5D52, true);
      d.setUint32(14, crc, true); d.setUint32(18, data.length, true); d.setUint32(22, data.length, true); d.setUint16(26, path.length, true);
      local.push(h, path, data);
      var c = new Uint8Array(46), v = new DataView(c.buffer);
      v.setUint32(0, 0x02014B50, true); v.setUint16(4, 20, true); v.setUint16(6, 20, true); v.setUint16(8, 0x800, true); v.setUint16(14, 0x5D52, true);
      v.setUint32(16, crc, true); v.setUint32(20, data.length, true); v.setUint32(24, data.length, true); v.setUint16(28, path.length, true); v.setUint32(42, offset, true);
      central.push(c, path); offset += h.length + path.length + data.length;
    });
    var directory = concat(central), end = new Uint8Array(22), v = new DataView(end.buffer), count = Object.keys(entries).length;
    v.setUint32(0, 0x06054B50, true); v.setUint16(8, count, true); v.setUint16(10, count, true); v.setUint32(12, directory.length, true); v.setUint32(16, offset, true);
    return concat(local.concat([directory, end]));
  }
  function ods(capture) {
    var content = '<?xml version="1.0" encoding="UTF-8"?><office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" office:version="1.2"><office:body><office:spreadsheet>';
    // Explicit standard styles keep native editors from inventing an invalid
    // font/number-format table when importing this small ODS package.
    var styles = '<?xml version="1.0" encoding="UTF-8"?><office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" xmlns:number="urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0" office:version="1.2"><office:font-face-decls><style:font-face style:name="LiberationSans" svg:font-family="Liberation Sans" style:font-family-generic="swiss" style:font-pitch="variable"/></office:font-face-decls><office:styles><number:number-style style:name="N0"><number:number number:min-integer-digits="1"/></number:number-style><style:default-style style:family="table-cell"><style:text-properties style:font-name="LiberationSans" fo:font-size="11pt"/></style:default-style><style:style style:name="Default" style:family="table-cell" style:data-style-name="N0"><style:text-properties style:font-name="LiberationSans" fo:font-size="11pt"/></style:style><style:style style:name="Header" style:family="table-cell" style:parent-style-name="Default"><style:text-properties fo:font-weight="bold"/></style:style></office:styles></office:document-styles>';
    capture.sheets.forEach(function (sheet) {
      content += '<table:table table:name="' + x(sheet.name) + '">';
      sheet.rows.forEach(function (row, index) {
        content += '<table:table-row>';
        row.forEach(function (value) {
          value = E.cell(value);
          var cell = '<table:table-cell table:style-name="' + (index === 0 ? 'Header' : 'Default') + '"';
          if (typeof value === "number") content += cell + ' office:value-type="float" office:value="' + value + '"><text:p>' + value + '</text:p></table:table-cell>';
          else if (typeof value === "boolean") content += cell + ' office:value-type="boolean" office:boolean-value="' + value + '"><text:p>' + value + '</text:p></table:table-cell>';
          else if (value === "") content += cell + '/>';
          else content += cell + ' office:value-type="string"><text:p>' + x(value).replace(/\n/g, '<text:line-break/>').replace(/\t/g, '<text:tab/>').replace(/ {2,}/g, function (s) { return '<text:s text:c="' + s.length + '"/>'; }) + '</text:p></table:table-cell>';
        });
        content += '</table:table-row>';
      });
      content += '</table:table>';
    });
    content += '</office:spreadsheet></office:body></office:document-content>';
    return zip({mimetype: "application/vnd.oasis.opendocument.spreadsheet", "content.xml": content, "styles.xml": styles,
      "META-INF/manifest.xml": '<?xml version="1.0" encoding="UTF-8"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2"><manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.spreadsheet" manifest:version="1.2"/><manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/><manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/></manifest:manifest>'});
  }
  function column(index) {
    var result = ""; for (index++; index; index = Math.floor((index - 1) / 26)) result = String.fromCharCode(65 + (index - 1) % 26) + result;
    return result;
  }
  function xlsx(capture) {
    var ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main", rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships", pkg = "http://schemas.openxmlformats.org/package/2006/relationships";
    var types = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>';
    var book = '<workbook xmlns="' + ns + '" xmlns:r="' + rel + '"><sheets>', relations = '<Relationships xmlns="' + pkg + '">', files = {};
    var strings = [], stringIds = new Map(), stringCount = 0;
    capture.sheets.forEach(function (sheet, index) {
      var id = index + 1, path = 'worksheets/sheet' + id + '.xml';
      types += '<Override PartName="/xl/' + path + '" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>';
      book += '<sheet name="' + x(sheet.name) + '" sheetId="' + id + '" r:id="rId' + id + '"/>';
      relations += '<Relationship Id="rId' + id + '" Type="' + rel + '/worksheet" Target="' + path + '"/>';
      var rows = sheet.rows.map(function (row, r) {
        return '<row r="' + (r + 1) + '">' + row.map(function (value, c) {
          value = E.cell(value); var ref = column(c) + (r + 1), style = r === 0 ? ' s="1"' : '';
          if (typeof value === "number") return '<c r="' + ref + '"' + style + '><v>' + value + '</v></c>';
          if (typeof value === "boolean") return '<c r="' + ref + '" t="b"' + style + '><v>' + Number(value) + '</v></c>';
          if (value === "") return '<c r="' + ref + '"' + style + '/>';
          // Shared strings preserve literal _xNNNN_ text in common office readers.
          if (!stringIds.has(value)) { stringIds.set(value, strings.length); strings.push(value); }
          stringCount++;
          return '<c r="' + ref + '" t="s"' + style + '><v>' + stringIds.get(value) + '</v></c>';
        }).join("") + '</row>';
      }).join("");
      files['xl/' + path] = '<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="' + ns + '"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols><col min="1" max="' + sheet.rows[0].length + '" width="22" customWidth="1"/></cols><sheetData>' + rows + '</sheetData>' + (sheet.name !== 'Read me' && sheet.rows.length > 1 ? '<autoFilter ref="A1:' + column(sheet.rows[0].length - 1) + sheet.rows.length + '"/>' : '') + '</worksheet>';
    });
    files['[Content_Types].xml'] = types + '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>';
    files['_rels/.rels'] = '<Relationships xmlns="' + pkg + '"><Relationship Id="rId1" Type="' + rel + '/officeDocument" Target="xl/workbook.xml"/></Relationships>';
    files['xl/workbook.xml'] = book + '</sheets></workbook>';
    files['xl/_rels/workbook.xml.rels'] = relations + '<Relationship Id="strings" Type="' + rel + '/sharedStrings" Target="sharedStrings.xml"/><Relationship Id="styles" Type="' + rel + '/styles" Target="styles.xml"/></Relationships>';
    files['xl/sharedStrings.xml'] = '<sst xmlns="' + ns + '" count="' + stringCount + '" uniqueCount="' + strings.length + '">' + strings.map(function (value) {
      value = value.replace(/_x[0-9a-fA-F]{4}_/g, function (s) { return '_x005F_' + s.slice(1); });
      return '<si><t xml:space="preserve">' + x(value).replace(/\r/g, '&#13;') + '</t></si>';
    }).join('') + '</sst>';
    files['xl/styles.xml'] = '<styleSheet xmlns="' + ns + '"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="2"><xf xfId="0"/><xf fontId="1" xfId="0" applyFont="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>';
    return zip(files);
  }
  return {ods: ods, xlsx: xlsx};
}());
if (typeof module !== "undefined" && module.exports) module.exports = OfficeWorkbook;
