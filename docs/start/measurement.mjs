import {BASE, readJSON} from './desk.mjs';
const STORAGE = 'financial-evidence-research-measurement-v1';
export function createMeasurement({operator = false} = {}) {
  const $ = id => document.getElementById(id), message = text => { $('measurement-status').textContent = text; };
  let identity = null;
  try { const saved = JSON.parse(localStorage.getItem(STORAGE) || 'null'); if (saved && /^fe_[A-Za-z0-9_-]{43}$/.test(saved.token) && Number.isFinite(saved.created)) identity = saved; } catch { /* Optional storage never prevents research. */ }
  const valid = () => !operator && identity?.enabled === true && Date.now() - identity.created < 30 * 86400000 && identity.created <= Date.now();
  const save = () => { try { if (identity) localStorage.setItem(STORAGE, JSON.stringify(identity)); else localStorage.removeItem(STORAGE); } catch { message('Browser storage is unavailable. This choice applies to this visit only.'); } };
  $('measurement').checked = valid();
  if (operator) { $('measurement').disabled = true; message('Operator verification: visitor measurement is disabled; research requests are labelled synthetic.'); }
  $('measurement').addEventListener('change', async () => {
    if (operator) return;
    if (!$('measurement').checked) { if (identity) identity.enabled = false; save(); message('Measurement disabled. You can delete earlier linked records below.'); return; }
    $('measurement').disabled = true;
    try {
      if (!identity) {
        const value = await readJSON(await fetch(`${BASE}/api/v1/applications`, {method:'POST',credentials:'omit',redirect:'error',headers:{'Content-Type':'application/json'},body:JSON.stringify({measurement_consent:true}),signal:AbortSignal.timeout(12000)}));
        if (!/^fe_[A-Za-z0-9_-]{43}$/.test(value.token)) throw new Error('Enrollment returned an invalid key.');
        identity = {token:value.token, created:Date.now(), enabled:false};
      }
      identity.enabled = true; identity.created = Date.now(); save(); message('Measurement enabled for future research requests. Past anonymous activity is not linked.');
    } catch (error) { $('measurement').checked = false; if (identity) identity.enabled = false; save(); message(`${error.message} Research still works with measurement off.`); }
    finally { $('measurement').disabled = false; }
  });
  $('forget').addEventListener('click', async () => {
    $('measurement').checked = false;
    if (!identity) { message('Measurement is off. This browser has no measurement key.'); return; }
    identity.enabled = false; save(); $('forget').disabled = true;
    try {
      const response = await fetch(`${BASE}/api/v1/applications/current`, {method:'DELETE',credentials:'omit',redirect:'error',headers:{Authorization:`Bearer ${identity.token}`},signal:AbortSignal.timeout(12000)});
      if (response.status !== 401 && (await readJSON(response)).deleted !== true) throw new Error('Deletion was not confirmed.');
      identity = null; save(); message('Linked measurement deleted or already expired. Anonymous aggregate counts remain.');
    } catch { message('Measurement is off. Deletion could not be confirmed; the disabled key remains here so you can retry.'); }
    finally { $('forget').disabled = false; }
  });
  return {get token() { return valid() && $('measurement').checked ? identity.token : ''; }};
}
