const BASE = 'https://api.seiche.info/funding-evidence';
const $ = id => document.getElementById(id);
const NAMES = {'policy.sofr':'SOFR','policy.effr':'Effective federal funds rate','policy.iorb':'Interest on reserve balances','distribution.sofr.p99':'SOFR 99th percentile','distribution.sofr.volume':'SOFR volume','liquidity.reserves':'Reserve balances (weekly average)','liquidity.tga':'Treasury General Account (opening)','liquidity.on_rrp':'Overnight reverse repo','liquidity.srf':'Standing repo facility'};
const operator = new URLSearchParams(location.search).get('operator') === '1';
let current = null;
let generation = 0;
let historical = false;
const storageKey = 'funding-measurement-v1';

async function response(path) {
  const result = await fetch(BASE + path, {cache:'no-store', credentials:'omit', signal:AbortSignal.timeout(15000)});
  if (!result.ok) throw new Error(`Evidence request unavailable (${result.status}).`);
  return result;
}
async function get(path) { return (await response(path)).json(); }
async function sha(bytes) { return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(x=>x.toString(16).padStart(2,'0')).join(''); }
function date(value) { return value ? new Date(value).toISOString().replace('T',' ').replace('.000Z',' UTC').replace(/\.\d+Z$/, ' UTC') : 'Unknown'; }
function text(id, value) { $(id).textContent = value; }
function cell(row, value, className='') { const node=document.createElement('td'); node.textContent=value; node.className=className; row.append(node); }
function notice(message, attention=false) { text('status',message); $('status').classList.toggle('attention',attention); }
function disableDownloads() { current=null; $('save-packet').disabled=true; $('save-csv').disabled=true; }

async function loadLatest(packetId='') {
  historical=Boolean(packetId);
  const run=++generation;
  disableDownloads(); notice('Checking the latest saved review…');
  try {
    const state=packetId ? {packet:{packet_id:packetId},ready:false} : await get('/latest');
    const id=state.packet?.packet_id;
    if (!/^\d{8}T\d{6}\.\d{6}Z-[a-f0-9]{32}$/.test(id)) throw new Error('No verified packet is available.');
    const [manifest, reviewBytes, csvBytes] = await Promise.all([
      get(`/packets/${id}/manifest.json`),
      response(`/packets/${id}/review.json`).then(r=>r.arrayBuffer()),
      response(`/packets/${id}/observations.csv`).then(r=>r.arrayBuffer())
    ]);
    if (manifest.packet_id!==id || await sha(reviewBytes)!==manifest.artifacts['review.json'] || await sha(csvBytes)!==manifest.artifacts['observations.csv']) throw new Error('The packet failed its integrity check.');
    const reviewText=new TextDecoder().decode(reviewBytes), csvText=new TextDecoder().decode(csvBytes);
    const review=JSON.parse(reviewText);
    if (review.capture_id!==id || !Array.isArray(review.results) || review.results.length!==9) throw new Error('The packet has an unexpected input set.');
    if (run!==generation) return;
    current={manifest,review,reviewText,csvText};
    $('observations').replaceChildren();
    for (const item of review.results) {
      const row=document.createElement('tr');
      cell(row,NAMES[item.metric_id]||item.metric_id);
      cell(row,item.value_state==='available' && Number.isFinite(item.value) ? `${item.value.toLocaleString('en-US',{maximumFractionDigits:6})} ${item.unit}` : item.value_state);
      cell(row,item.observation_date||'Unknown');
      cell(row,`${item.review_status}${item.newer_observation_available===true ? ' · newer observation exists' : ''}`);
      cell(row,item.source||'Unknown','source'); $('observations').append(row);
    }
    text('review-date',review.review_asof||'Mixed observation dates'); text('captured',date(review.captured_at)); text('archived',date(manifest.archived_at));
    $('exceptions').replaceChildren();
    for(const issue of review.issues||[]) { const li=document.createElement('li'); li.textContent=`${issue.subject}: ${issue.code}`; $('exceptions').append(li); }
    notice(packetId ? 'Historical packet: values and checks are retained as captured. This is not the current review.' : state.ready ? 'Required checks passed for this dated review. Check each observation date before use.' : 'This captured review needs attention. Inspect the exceptions before using it.', !state.ready);
    const link=$('manifest-link'); link.href=`${BASE}/packets/${id}/manifest.json`; link.hidden=false; link.textContent='Packet manifest';
    $('save-packet').disabled=false; $('save-csv').disabled=false;
  } catch(error) {
    if(run!==generation) return;
    disableDownloads(); notice(`${error.message} An earlier success is not shown as current.`,true);
    for(const id of ['review-date','captured','archived']) text(id,'—'); $('manifest-link').hidden=true; $('exceptions').replaceChildren();
    $('observations').replaceChildren(); const row=document.createElement('tr'); cell(row,'Current evidence unavailable'); row.firstChild.colSpan=5; $('observations').append(row);
  }
}

function savedConsent() {
  try { const value=JSON.parse(localStorage.getItem(storageKey)||'null'); return value && /^[a-f0-9]{32}$/.test(value.visitor) && Date.now()-value.created<30*86400000 ? value : null; } catch { return null; }
}
async function measure(packetId) {
  const value=savedConsent();
  if(operator || !value || value.enabled!==true || !$('consent').checked) return;
  try { await fetch(BASE+'/events',{method:'POST',credentials:'omit',headers:{'Content-Type':'application/json'},body:JSON.stringify({visitor:value.visitor,consent:true,packet_id:packetId,kind:'packet_download',traffic_class:'browser'}),signal:AbortSignal.timeout(5000)}); } catch { /* Measurement never blocks research. */ }
}
function download(raw, name, type) {
  const a=document.createElement('a'), url=URL.createObjectURL(new Blob([raw],{type})); a.href=url; a.download=name; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
}
$('save-packet').addEventListener('click',()=>{ if(!current)return; const value={schema:'financial-evidence.portable-research-packet.v1',manifest:current.manifest,review_json:current.reviewText,observations_csv:current.csvText}; download(JSON.stringify(value,null,2)+'\n',`funding-${current.manifest.packet_id}.json`,'application/json'); void measure(current.manifest.packet_id); });
$('save-csv').addEventListener('click',()=>{ if(!current)return; download(current.csvText,`funding-${current.manifest.packet_id}.csv`,'text/csv'); void measure(current.manifest.packet_id); });
$('consent').checked=savedConsent()?.enabled===true;
$('consent').addEventListener('change',async()=>{
  if($('consent').checked) { try { const previous=savedConsent(); localStorage.setItem(storageKey,JSON.stringify(previous ? {...previous,enabled:true} : {visitor:crypto.randomUUID().replaceAll('-',''),created:Date.now(),enabled:true})); text('privacy-status','Optional measurement enabled.'); } catch { $('consent').checked=false; text('privacy-status','Browser storage unavailable; measurement stays off.'); } }
  else await forget();
});
async function forget() {
  const value=savedConsent();
  $('consent').checked=false;
  try { if(value) localStorage.setItem(storageKey,JSON.stringify({...value,enabled:false})); } catch { /* In-memory choice still disables this page. */ }
  try { if(value) { const result=await fetch(BASE+'/forget',{method:'POST',credentials:'omit',headers:{'Content-Type':'application/json'},body:JSON.stringify({visitor:value.visitor,consent:true}),signal:AbortSignal.timeout(10000)}); if(!result.ok)throw new Error('Deletion unavailable'); } localStorage.removeItem(storageKey); $('consent').checked=false; text('privacy-status','Usage removed and measurement disabled.'); }
  catch { $('consent').checked=false; text('privacy-status','Measurement disabled. Deletion could not be confirmed; retry Forget my usage. Records expire after 30 days.'); }
}
$('forget').addEventListener('click',forget);

async function loadHistory(asOf='') {
  try {
    const data=await get('/history'+(asOf?'?as_of='+encodeURIComponent(asOf):''));
    text('coverage',data.packet_count ? `${data.packet_count} packets first archived from ${date(data.first_archived_at)}. ${data.truncated?'Showing the latest 96.':''}` : 'No packet had been verified in this archive by that time.');
    for(const id of ['before','after']) { const select=$(id); select.replaceChildren(); for(const item of data.packets) { const option=document.createElement('option'); option.value=item.packet_id; option.textContent=`${date(item.archived_at)} · review ${item.review_asof||'mixed dates'}`; select.append(option); } }
    if(data.packets.length) $('after').value=data.packets.at(-1).packet_id;
    text('history-status',data.latest_attempt?.error ? 'The latest acquisition by that time failed. Earlier packets remain historical evidence.' : '');
  } catch(error) { text('history-status',error.message); }
}
$('query-history').addEventListener('click',()=>{ const value=$('as-of').value; if(!value){text('history-status','Choose a UTC time first.');return;} void loadHistory(value+(value.length===16?':00Z':'Z')); });
$('open-history').addEventListener('click',()=>{const id=$('after').value;if(id)void loadLatest(id);});
$('show-latest').addEventListener('click',()=>{ $('as-of').value=''; void loadLatest(); void loadHistory(); });
$('compare').addEventListener('click',async()=>{
  const before=$('before').value, after=$('after').value;
  if(!before||!after){text('history-status','Select two retained packets.');return;}
  try { const result=await get('/compare?before='+encodeURIComponent(before)+'&after='+encodeURIComponent(after)); const list=document.createElement('ul'); for(const change of result.changes){const li=document.createElement('li');li.textContent=`${NAMES[change.metric_id]||change.metric_id}: ${change.before.value??change.before.value_state} → ${change.after.value??change.after.value_state}; ${change.before.observation_date} → ${change.after.observation_date}. ${change.kind.replaceAll('_',' ')}.`;list.append(li);} $('comparison').replaceChildren(list); text('history-status',result.changes.length ? 'Differences between saved observations; not a claim of publisher revision events.' : 'No input values, dates, units, sources or availability states changed between these packets.'); }
  catch(error){text('history-status',error.message);}
});
async function loadReliability(){try{const data=await get('/reliability'), p=data.perspectives.hetzner_same_host;if(!p){text('reliability-status','The observation record has just started.');return;}text('reliability-status',`${p.observed_slots} observed / ${p.expected_slots} expected sampling slots; ${p.missing_slots} missing. ${p.available_observed_slots} available and ${p.ready_observed_slots} data-ready. Record spans ${p.baseline_elapsed_days.toFixed(2)} days. ${p.thirty_days_elapsed?'A 30-day window is available for review.':'The 30-day record is still accumulating.'}`);}catch(error){text('reliability-status',error.message);}}
void Promise.allSettled([loadLatest(),loadHistory(),loadReliability()]);
setInterval(()=>{ if(!document.hidden && !historical) void Promise.allSettled([loadLatest(),loadReliability()]); },300000);
document.addEventListener('visibilitychange',()=>{ if(!document.hidden && !historical) void loadLatest(); });
