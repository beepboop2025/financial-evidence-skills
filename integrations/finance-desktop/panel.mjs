import {currencies, loadSeries, noteFor} from './reference-fx.mjs';
const currency = document.querySelector('#currency');
const button = document.querySelector('#refresh');
const status = document.querySelector('#status');
const result = document.querySelector('#result');
const rows = document.querySelector('#rows');
const source = document.querySelector('#source');
const download = document.querySelector('#download');
let noteURL;
const selected = new URLSearchParams(location.search).get('currency');
if (currencies.includes(selected)) currency.value = selected;

button.addEventListener('click', async () => {
  button.disabled = true;
  result.hidden = true;
  download.hidden = true;
  rows.replaceChildren();
  source.textContent = '';
  status.textContent = 'Fetching source-dated reference observations…';
  if (noteURL) { URL.revokeObjectURL(noteURL); noteURL = undefined; }
  try {
    const data = await loadSeries(currency.value);
    const fetchedAt = new Date().toISOString();
    status.textContent = `Latest observation: ${data.lastObservation}. Source-reported freshness: ${data.staleness}. Browser fetched: ${fetchedAt}.`;
    document.querySelector('#unit').textContent = data.unit;
    for (const row of data.rows.slice(-10).reverse()) {
      const tr = document.createElement('tr');
      for (const value of [row.date, row.value]) {
        const td = document.createElement('td'); td.textContent = value; tr.append(td);
      }
      rows.append(tr);
    }
    source.textContent = data.comments;
    noteURL = URL.createObjectURL(new Blob([noteFor(data, fetchedAt)], {type: 'text/plain;charset=utf-8'}));
    download.href = noteURL;
    download.download = `seiche-${data.currency}-review-${data.lastObservation}.txt`;
    result.hidden = false;
    download.hidden = false;
  } catch (error) {
    status.textContent = `${error.message} No value is substituted. You can retry or inspect the original source below.`;
  } finally { button.disabled = false; }
});
window.addEventListener('pagehide', () => { if (noteURL) URL.revokeObjectURL(noteURL); });
