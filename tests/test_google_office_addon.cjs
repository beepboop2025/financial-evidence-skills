const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const {row,funding,institutions}=require('./office-fixtures.cjs');
const root=path.resolve(__dirname,'..');
const addon=path.join(root,'docs/office/marketplaces/google');
const code=fs.readFileSync(path.join(addon,'Code.gs'),'utf8');

function harness(config={}) {
  const state={requests:[],sheets:[],releases:0,locks:0,menu:[],active:null,uuid:0};
  const existing={name:'My analysis',cells:[['Keep my analysis',42]]};
  const original=JSON.stringify(existing);
  function makeSheet(name) {
    const sheet={name,cells:null,formats:null,filter:false};
    // Explicit documented return types; an unknown API must not become a fluent method.
    const chain={
      setValues(values){if(config.writeFails) throw new Error('provider private failure');sheet.cells=values;return this;},
      setNumberFormats(formats){sheet.formats=formats;return this;},
      createFilter(){sheet.filter=true;return {type:'Filter'};},
      setVerticalAlignment(){return this;},setFontWeight(){return this;},
      setBackground(){return this;},setFontColor(){return this;},setWrap(){return this;}
    };
    sheet.getRange=()=>chain;
    // Google documents setFrozenRows as void; it is not chainable like sizing.
    sheet.setFrozenRows=(count)=>{sheet.frozenRows=count;};
    sheet.setColumnWidths=(start,count,width)=>{sheet.columnWidths=[start,count,width];return sheet;};
    sheet.setColumnWidth=()=>sheet;
    return sheet;
  }
  const workbook={getSheetByName:()=>config.collision ? existing : null,
    insertSheet:(name)=>{const s=makeSheet(name);state.sheets.push(s);return s;},
    setActiveSheet:(s)=>{state.active=s;}};
  const menu={addItem(name,fn){state.menu.push([name,fn]);return this;},addToUi(){}};
  const ui={createAddonMenu(){return menu;},showSidebar(){state.sidebar=true;}};
  const context=vm.createContext({console,
    SpreadsheetApp:{getUi:()=>ui,getActiveSpreadsheet:()=>workbook,flush:()=>{}},
    LockService:{getDocumentLock:()=>({tryLock:()=>{state.locks++;return !config.busy;},releaseLock:()=>state.releases++})},
    Utilities:{getUuid:()=>String(++state.uuid).padStart(3,'0')+'-test'},
    HtmlService:{createHtmlOutputFromFile:()=>({setTitle(){return this;}})},
    UrlFetchApp:{fetchAll:(requests)=>{
      state.requests.push(...requests);
      if(config.networkFails) throw new Error('secret upstream detail');
      return requests.map((request,i)=>{
        const url=new URL(request.url),kind=url.searchParams.get('workflow');
        const data=kind==='funding'?funding(url.searchParams.get('selection'),[row(0),row(null),row(-2),row(4,{rights_status:'restricted'}),row(1,{context:'=2+3'})]):institutions();
        return {getHeaders:()=>({'Content-Type':config.html?'text/html':'application/json'}),
          getResponseCode:()=>config.badFirst&&i===0?500:200,
          getContent:()=>({length:config.oversized?4*1024*1024+1:JSON.stringify(data).length}),
          getContentText:()=>JSON.stringify(data)};
      });
    }}
  });
  vm.runInContext(code,context);
  return {state,context,existing,original};
}
const options={currencies:'USD,EUR',institutions:'au-sfb,unknown-bank',verification:true};
test('manifest is limited to current workbook, external requests and sidebar',()=>{
  const manifest=JSON.parse(fs.readFileSync(path.join(addon,'appsscript.json')));
  assert.deepEqual(manifest.oauthScopes,['https://www.googleapis.com/auth/spreadsheets.currentonly','https://www.googleapis.com/auth/script.external_request','https://www.googleapis.com/auth/script.container.ui']);
  assert.deepEqual(manifest.urlFetchWhitelist,['https://agents.seiche.info/v1/research/api/v1/']);
  assert.equal(manifest.exceptionLogging,'NONE');
});
test('no-auth lifecycle only builds a menu, without requests or cell reads',()=>{
  const {context,state}=harness();context.onOpen({authMode:'NONE'});context.onInstall({});
  assert.equal(state.menu.length,2);assert.equal(state.requests.length,0);assert.equal(state.sheets.length,0);
  assert.ok(!/getValues\(|getDisplayValues\(|getDataRange\(|DriveApp|GmailApp|PropertiesService|newTrigger/.test(code));
});
test('real shared parser preserves gaps, numeric states and original JSON in dedicated tabs',()=>{
  const {context,state,existing,original}=harness();
  const result=context.insertOfficeReview(options);
  assert.equal(state.requests.length,3);assert.equal(state.sheets.length,6);assert.equal(result.failed_requests,0);
  assert.equal(JSON.stringify(existing),original);assert.equal(state.releases,1);
  assert.ok(state.sheets.every(sheet=>sheet.frozenRows===1&&sheet.columnWidths[0]===1&&sheet.columnWidths[2]===170));
  const fundingSheet=state.sheets.find(s=>s.name.endsWith('Funding'));
  const cols=fundingSheet.cells[0], value=cols.indexOf('value'), valueState=cols.indexOf('value_state');
  assert.equal(fundingSheet.cells[1][value],0);assert.equal(fundingSheet.cells[2][value],'');
  assert.equal(fundingSheet.cells[3][value],-2);assert.equal(fundingSheet.cells[4][value],'');
  assert.equal(fundingSheet.cells[4][valueState],'withheld_by_client');
  assert.equal(fundingSheet.cells[5][cols.indexOf('context')],"'=2+3");
  assert.equal(fundingSheet.formats[1][cols.indexOf('as_of')],'@');
  assert.equal(fundingSheet.formats[1][value],'General');
  assert.match(JSON.stringify(state.sheets.find(s=>s.name.endsWith('Institutions')).cells),/unknown-bank/);
  assert.match(JSON.stringify(state.sheets.find(s=>s.name.endsWith('Gaps')).cells),/No current reviewed disclosure/);
  assert.equal(JSON.parse(result.evidence_json).requests.length,3);
  for(const r of state.requests){assert.equal(r.followRedirects,false);assert.equal(r.validateHttpsCertificates,true);assert.equal(r.headers['X-Liquilens-Traffic-Class'],'synthetic');assert.equal(r.headers['X-Financial-Evidence-Traffic-Class'],'synthetic');}
});
test('repeat refresh never reuses the first capture or alters existing analysis',()=>{
  const {context,state,existing,original}=harness();
  const first=context.insertOfficeReview(options);const second=context.insertOfficeReview(options);
  assert.equal(state.sheets.length,12);assert.equal(new Set([...first.sheet_names,...second.sheet_names]).size,12);
  assert.equal(JSON.stringify(existing),original);assert.equal(state.releases,2);
});
test('bad selections and unsupported options cause no fetches or writes',()=>{
  for(const selection of [{},{currencies:'USD,EUR,INR,GBP,JPY,CAD'},{currencies:'https://example.com'},{currencies:'USD',datasets:['money_markets']},{currencies:'USD',verification:'true'}]){
    const {context,state}=harness();assert.throws(()=>context.insertOfficeReview(selection));
    assert.equal(state.requests.length,0);assert.equal(state.sheets.length,0);
  }
});
test('one bad response retains successful research and explicit status',()=>{
  for(const config of [{badFirst:true},{html:true},{oversized:true}]){
    const {context,state}=harness(config);const result=context.insertOfficeReview(options);
    assert.ok(result.failed_requests>0);assert.equal(state.sheets.length,6);
    assert.match(JSON.stringify(state.sheets.find(s=>s.name.endsWith('Status')).cells),/failed/);
  }
});
test('transport, lock, collision and partial-write failures are bounded and release locks',()=>{
  for(const config of [{networkFails:true},{busy:true},{collision:true},{writeFails:true}]){
    const {context,state,existing,original}=harness(config);
    assert.throws(()=>context.insertOfficeReview(options),error=>!error.message.includes('secret')&&!error.message.includes('private'));
    assert.equal(state.sheets.length,config.writeFails?1:0);assert.equal(state.releases,config.busy?0:1);
    assert.equal(JSON.stringify(existing),original);
  }
});
test('ordinary calls are unverified and carry no credentials or workbook data',()=>{
  const {context,state}=harness();context.insertOfficeReview({currencies:'USD'});
  assert.equal(state.requests.length,1);
  assert.equal(state.requests[0].headers['X-Financial-Evidence-Traffic-Class'],'unverified');
  assert.equal(state.requests[0].headers['X-Liquilens-Traffic-Class'],undefined);
  assert.ok(!JSON.stringify(state.requests).includes('Keep my analysis'));
});

test('sidebar uses official styling and an accessible error dialog with safe retry',()=>{
  const html=fs.readFileSync(path.join(addon,'Sidebar.html'),'utf8');
  assert.match(html,/<link rel="stylesheet" href="https:\/\/ssl\.gstatic\.com\/docs\/script\/css\/add-ons1\.css">/);
  assert.equal((html.match(/class="action"/g)||[]).length,1);
  assert.match(html,/<dialog id="error-dialog" aria-labelledby="error-title" aria-describedby="error-detail">/);
  assert.match(html,/id="evidence" class="button download secondary"/);
  const state={focus:null,calls:[],revoked:[]}, elements={};
  for(const [,id] of html.matchAll(/id="([^"]+)"/g)) {
    elements[id]={value:'',hidden:id==='evidence',disabled:false,open:false,handlers:{},
      addEventListener(event,handler){this.handlers[event]=handler;},
      removeAttribute(key){delete this[key];},
      focus(){state.focus=id;},
      showModal(){this.open=true;},
      close(){this.open=false;this.handlers.close?.();}};
  }
  elements.currencies.value='USD';elements.institutions.value='';
  const runner={withSuccessHandler(fn){this.success=fn;return this;},withFailureHandler(fn){this.failure=fn;return this;},
    insertOfficeReview(options){state.calls.push(options);}};
  vm.runInNewContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],{
    document:{getElementById:id=>elements[id]},google:{script:{run:runner}},Blob,
    URL:{createObjectURL:()=> 'blob:review',revokeObjectURL:url=>state.revoked.push(url)}
  });
  assert.equal(state.calls.length,0);
  const submit=()=>elements.review.handlers.submit({preventDefault(){}});
  submit();submit();assert.equal(state.calls.length,1);assert.equal(elements.refresh.disabled,true);
  const errorText='Invalid selection <img src=x>. Use at most five currencies.';
  runner.failure({message:errorText});
  assert.equal(elements['error-dialog'].open,true);assert.equal(state.focus,'error-close');
  assert.equal(elements['error-detail'].textContent,errorText);assert.equal(elements['error-detail'].innerHTML,undefined);
  assert.equal(elements.status.textContent,errorText);assert.equal(elements.evidence.hidden,true);
  elements['error-close'].handlers.click();
  assert.equal(elements['error-dialog'].open,false);assert.equal(state.focus,'refresh');
  submit();runner.success({sheet_names:Array(6),captured_at:'2026-10-18T09:00:00Z',failed_requests:0,request_count:1,evidence_json:'{}'});
  assert.equal(elements.refresh.disabled,false);assert.equal(elements.evidence.hidden,false);
  assert.equal(elements.evidence.href,'blob:review');
  submit();assert.deepEqual(state.revoked,['blob:review']);assert.equal(elements.evidence.hidden,true);
});
