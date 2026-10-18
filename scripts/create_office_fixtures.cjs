// Offline acceptance artifacts, deliberately synthetic. No product API requests.
const fs=require('node:fs'),path=require('node:path');
const E=require('../docs/office/office-core.js'),W=require('../docs/office/workbook.js');
const {row,funding,institutions}=require('../tests/office-fixtures.cjs');
const dir=process.argv[2];if(!dir)throw new Error('Output directory required');fs.mkdirSync(dir,{recursive:true});
const requests=E.plan({currencies:'USD',institutions:'au-sfb,unknown-bank'});
const capture=E.bundle([E.project(requests[0],funding('USD',[row(0,{entity_name:'=2+3',context:'Unicode ₹ € 中 & <source> _x0041_'}),row(null),row(-2),row(99,{rights_status:'restricted'})])),E.project(requests[1],institutions())]);
for(const [name,bytes]of Object.entries({'review.ods':W.ods(capture),'review.xlsx':W.xlsx(capture),'expected.json':JSON.stringify(capture.sheets,null,2)}))fs.writeFileSync(path.join(dir,name),bytes);
