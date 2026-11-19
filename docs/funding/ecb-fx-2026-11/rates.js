const snapshot = "https://huggingface.co/datasets/liquilens/seiche-ecb-reference-fx/resolve/6a69269e2a5ce104defe87681203705ccc4876db/data/ecb_reference_fx_daily.csv";
const digest = "d2c2ab02a8352c72cc539d420052ae8f09b98abbeacc4415cfbdacef5f2389ad";
const currencies = ["USD", "INR", "GBP", "JPY"];
const field = id => document.getElementById(id);
const controls = Object.fromEntries(["base", "quote", "year", "date", "lag"].map(id => [id, field(id)]));
const rateFormat = new Intl.NumberFormat("en", {maximumSignificantDigits: 8});
let observations;
let dates = [];
let plotted = [];

function choices(select, values, chosen) {
  select.replaceChildren(...values.map(value => new Option(value, value)));
  select.value = chosen;
}

async function loadObservations() {
  const response = await fetch(snapshot, {credentials: "omit", signal: AbortSignal.timeout(20000)});
  if (!response.ok) throw new Error("Snapshot download failed.");
  const bytes = await response.arrayBuffer();
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  const hex = Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, "0")).join("");
  if (hex !== digest) throw new Error("Snapshot checksum differs from the published version.");
  const rows = new TextDecoder().decode(bytes).trimEnd().split(/\r?\n/);
  if (rows.shift() !== "date,currency,value_per_eur") throw new Error("Unexpected CSV columns.");
  const byDate = new Map();
  for (const row of rows) {
    const [date, currency, rate] = row.split(",");
    if (!byDate.has(date)) byDate.set(date, {});
    byDate.get(date)[currency] = rate;
  }
  return byDate;
}

function setDates(preferred) {
  dates = Array.from(observations.keys()).filter(day => {
    const row = observations.get(day);
    return row[controls.base.value] && row[controls.quote.value];
  }).sort();
  const selected = dates.includes(preferred) ? preferred : dates.at(-1);
  choices(controls.year, [...new Set(dates.map(d => d.slice(0, 4)))].reverse(), selected.slice(0, 4));
  setYear(selected);
}

function setYear(preferred) {
  const days = dates.filter(day => day.startsWith(controls.year.value)).reverse();
  choices(controls.date, days, days.includes(preferred) ? preferred : days[0]);
}

function drawChart() {
  if (!plotted.length) return;
  const canvas = field("chart");
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (!w || !h) return;
  const scale = window.devicePixelRatio || 1;
  canvas.width = Math.round(w * scale);
  canvas.height = Math.round(h * scale);
  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);
  const rates = plotted.map(point => point.rate);
  const lo = Math.min(...rates), hi = Math.max(...rates);
  const start = plotted[0].time, end = plotted.at(-1).time;
  ctx.font = "11px system-ui";
  ctx.fillStyle = "#c9dbf2";
  ctx.fillText(rateFormat.format(hi), 2, 12);
  if (lo !== hi) ctx.fillText(rateFormat.format(lo), 2, h - 2);
  ctx.beginPath();
  for (const {time, rate} of plotted) {
    const x = 3 + (w - 6) * (time - start) / (end - start);
    const y = lo === hi ? h / 2 : 22 + (h - 44) * (hi - rate) / (hi - lo);
    ctx.lineTo(x, y);
  }
  ctx.strokeStyle = "#a3dbf5";
  ctx.lineWidth = 2;
  ctx.stroke();
}

function render() {
  const {base, quote, date, lag} = Object.fromEntries(Object.entries(controls).map(([key, el]) => [key, el.value]));
  const last = dates.indexOf(date);
  const first = last - Number(lag);
  const prior = first >= 0 ? dates[first] : null;
  const cross = day => observations.get(day)[quote] / observations.get(day)[base];
  const unit = quote + " per " + base;
  field("unit").textContent = unit + " on " + date;
  field("rate").textContent = rateFormat.format(cross(date));
  field("formula").textContent = "Divide " + quote + " per EUR by " + base + " per EUR on each date.";
  field("base-unit").textContent = base + " per EUR";
  field("quote-unit").textContent = quote + " per EUR";
  field("result-unit").textContent = unit;
  field("values").replaceChildren();
  for (const day of [prior, date].filter(Boolean)) {
    const tr = field("values").insertRow();
    for (const value of [day, observations.get(day)[base], observations.get(day)[quote], rateFormat.format(cross(day))]) {
      tr.insertCell().textContent = value;
    }
  }
  field("plot").hidden = !prior;
  plotted = [];
  if (prior) {
    const change = (cross(date) / cross(prior) - 1) * 100;
    const delta = new Intl.NumberFormat("en", {maximumFractionDigits: 3, signDisplay: "exceptZero"}).format(change);
    field("movement").textContent = delta + "% since " + prior + " (" + rateFormat.format(cross(prior)) + " " + unit + ").";
    field("earlier").textContent = prior;
    field("later").textContent = date;
    plotted = dates.slice(first, last + 1).map(day => ({time: Date.parse(day), rate: cross(day)}));
    field("chart").setAttribute("aria-label", unit + " from " + prior + " to " + date + ". Start and end observations appear in the table.");
    drawChart();
  } else {
    field("movement").textContent = "The snapshot has fewer than " + lag + " earlier shared observations for this selection.";
  }
  const url = new URL(location.pathname, location.origin);
  url.search = new URLSearchParams({base, quote, date, lag});
  field("permalink").href = url.href;
}

async function start() {
  observations = await loadObservations();
  const query = new URLSearchParams(location.search);
  const requested = Object.fromEntries(["base", "quote", "date", "lag"].map(key => [key, query.get(key)]));
  const base = currencies.includes(requested.base) ? requested.base : "USD";
  const quotes = currencies.filter(code => code !== base);
  const quote = quotes.includes(requested.quote) ? requested.quote : quotes[0];
  choices(controls.base, currencies, base);
  choices(controls.quote, quotes, quote);
  if (Array.from(controls.lag.options).some(opt => opt.value === requested.lag)) controls.lag.value = requested.lag;
  else controls.lag.value = "20";
  setDates(requested.date);
  const invalidLink = Object.entries(requested).some(([key, value]) => value !== null && value !== controls[key].value);
  field("status").textContent = invalidLink ? "This link requests an unavailable selection. The controls show an available comparison." : "";
  field("calculator").hidden = false;
  field("calculator").addEventListener("change", event => {
    if (event.target === controls.base) {
      const available = currencies.filter(code => code !== controls.base.value);
      choices(controls.quote, available, available.includes(controls.quote.value) ? controls.quote.value : available[0]);
    }
    if (event.target === controls.base || event.target === controls.quote) {
      const previous = controls.date.value;
      setDates(previous);
      field("status").textContent = controls.date.value === previous ? "" : "The new pair has no observation for the previous date. Showing its latest shared date.";
    } else {
      field("status").textContent = "";
    }
    if (event.target === controls.year) setYear();
    render();
    history.replaceState(null, "", field("permalink").href);
  });
  new ResizeObserver(drawChart).observe(field("plot"));
  render();
}

start().catch(error => {
  field("calculator").hidden = true;
  field("status").textContent = "The verified snapshot could not be loaded. " + error.message + " You can inspect the source files below.";
});
