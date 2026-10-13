import {readJSON} from './desk.mjs';
const STORAGE = 'financial-evidence-research-measurement-v1';
const LEGACY_DELETE = 'https://api.seiche.info/openbb/api/v1/applications/current';

// Legacy keys belong only to their issuing service. They never authenticate
// central research or new learning enrollment.
export function createMeasurement({operator = false} = {}) {
  const $ = id => document.getElementById(id);
  const message = text => { $('measurement-status').textContent = text; };
  let identity = null;
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE) || 'null');
    if (saved && /^fe_[A-Za-z0-9_-]{43}$/.test(saved.token)) identity = saved;
  } catch { /* Storage is optional; public research stays available. */ }
  const save = () => {
    try {
      if (identity) localStorage.setItem(STORAGE, JSON.stringify(identity));
      else localStorage.removeItem(STORAGE);
    } catch { message('Browser storage is unavailable. Public research still works.'); }
  };
  if (identity) { identity.enabled = false; save(); }
  $('forget').hidden = !identity;
  message(operator
    ? 'Operator verification: research requests are labelled synthetic.'
    : 'Public research uses bounded hosted operational counts. Optional learning requires a separate owner-authorized enrollment.');
  $('forget').addEventListener('click', async () => {
    if (!identity) { message('This browser has no legacy measurement key.'); return; }
    $('forget').disabled = true;
    try {
      const response = await fetch(LEGACY_DELETE, {method:'DELETE', credentials:'omit', redirect:'error', headers:{Authorization:`Bearer ${identity.token}`}, signal:AbortSignal.timeout(12000)});
      if (response.status !== 401 && (await readJSON(response)).deleted !== true) throw new Error('Deletion was not confirmed.');
      identity = null; save(); $('forget').hidden = true;
      message('Legacy linked measurement deleted or already expired. Anonymous aggregate counts remain.');
    } catch {
      message('Legacy attribution is off. Deletion could not be confirmed; the disabled key remains here so you can retry.');
    } finally { $('forget').disabled = false; }
  });
  return {get token() { return ''; }};
}
