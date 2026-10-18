(function () {
  'use strict';
  var E=OfficeEvidence, capture=null, hostReady=false, busy=false;
  var $=function(id){return document.getElementById(id);};
  var verification=new URLSearchParams(location.search).get('operator')==='1';
  function controls(){$('refresh').disabled=busy;$('insert').disabled=busy||!capture||!hostReady;$('currencies').disabled=busy;$('institutions').disabled=busy;}
  function message(text,error){$('status').textContent=text;$('status').classList.toggle('error',Boolean(error));}
  function clear(){capture=null;$('review').hidden=true;$('summary').replaceChildren();$('preview').replaceChildren();controls();}
  function preview(sheet,columns){
    if(sheet.rows.length<2)return;
    var details=document.createElement('details'),label=document.createElement('summary'),wrap=document.createElement('div'),table=document.createElement('table');
    label.textContent=sheet.name+' preview';details.append(label);wrap.className='table-scroll';wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label',sheet.name+' preview');
    var indices=columns.map(function(c){return sheet.rows[0].indexOf(c);});
    sheet.rows.slice(0,6).forEach(function(row,index){var tr=document.createElement('tr');indices.forEach(function(i){var td=document.createElement(index?'td':'th');if(!index)td.scope='col';td.textContent=row[i]===''?'—':String(row[i]);tr.append(td);});table.append(tr);});
    wrap.append(table);details.append(wrap);var note=document.createElement('p');note.className='hint';note.textContent='First five rows. All returned rows, source URLs and request status are included in the new sheets.';details.append(note);$('preview').append(details);
  }
  if(typeof Office!=='undefined') Office.onReady(function(info){
    hostReady=info.host===Office.HostType.Excel&&Office.context.requirements.isSetSupported('ExcelApi','1.1');
    $('host-status').textContent=hostReady?'Connected to Excel. Insertions create new sheets.':'Open this add-in inside Excel to insert sheets. Browser downloads are available at the office desk.';controls();
  });
  else $('host-status').textContent='Excel is unavailable here. Use the office desk to download a workbook.';
  $('review-form').addEventListener('input',clear);
  $('review-form').addEventListener('submit',async function(event){
    event.preventDefault();if(busy)return;clear();busy=true;controls();
    $('currencies').disabled=true;$('institutions').disabled=true;
    try{
      var options={currencies:$('currencies').value,institutions:$('institutions').value,verification:verification};
      E.plan(options);message('Retrieving research. Each request is limited to 30 seconds.');
      capture=await E.run(options);
      var failed=capture.requests.filter(function(r){return r.status.request_status==='failed';}).length;
      if(failed===capture.requests.length){capture=null;throw new Error('No requests returned usable research. Retry manually; previous values were not reused.');}
      capture.sheets.filter(function(s){return s.name!=='Read me';}).forEach(function(s){var li=document.createElement('li');li.textContent=s.name+': '+(s.rows.length-1)+' rows';$('summary').append(li);});
      preview(capture.sheets[1],['selection','metric','value','unit','as_of','value_state']);
      preview(capture.sheets[2],['slug','status','latest_period','coverage_complete']);
      preview(capture.sheets[3],['slug','field','status','reason']);
      $('review-time').textContent='Captured '+capture.captured_at+'. Check source dates before comparing rows.';
      $('scope').textContent=E.NOTE;$('review').hidden=false;
      message(failed?failed+' request(s) failed. Status and gaps will be inserted with the returned rows.':'Research returned. Review its dates and coverage, then insert.',failed>0);
    }catch(error){clear();message(error.message,true);}finally{busy=false;$('currencies').disabled=false;$('institutions').disabled=false;controls();}
  });
  $('insert').addEventListener('click',async function(){
    if(busy||!capture||!hostReady)return;busy=true;controls();
    try{var names=await OfficeInsert.insert(capture,Excel,new Date().toISOString().replace(/\D/g,'').slice(4,14));message('Inserted '+names.length+' new review sheets. Source dates and gaps are included.');}
    catch(error){message(error.message,true);}finally{busy=false;controls();}
  });
  $('evidence').addEventListener('click',function(){
    if(!capture)return;var url=URL.createObjectURL(new Blob([JSON.stringify(capture,null,2)+'\n'],{type:'application/json'}));
    var a=document.createElement('a');a.href=url;a.download='financial-evidence.json';document.body.append(a);a.click();a.remove();setTimeout(function(){URL.revokeObjectURL(url);},1000);
  });
}());
