const SYNTHETIC_PACKET = Object.freeze({
  schema: "liquidity-lab.financial-evidence-packet.v1",
  status: "complete",
  transport_status: "complete",
  status_semantics: "transport_only",
  evidence_status: "not_evaluated",
  carrier_verification: "not_performed",
  topics: ["money-market", "china-economy"],
  sources: [
    {
      topic: "money-market",
      product: "Seiche",
      ok: true,
      carrier_state: "not_published",
      source_reported: {
        adapter: "synthetic_example",
        state: [{ name: "response_status", value: "PARTIAL" }],
        clocks: [{ name: "generated_at", value: "2030-01-01T00:00:00Z" }],
      },
    },
    {
      topic: "china-economy",
      product: "Palimpsest",
      ok: true,
      carrier_state: "not_published",
      source_reported: {
        adapter: "synthetic_example",
        state: [{ name: "readiness", value: "warming_up" }],
        clocks: "not_reported",
      },
    },
  ],
  synthetic_example: true,
});

function object(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function token(value, fallback) {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function formatReported(value) {
  if (!Array.isArray(value) || !value.length) return token(value, "not reported");
  return value
    .filter((item) => object(item) && typeof item.name === "string")
    .map((item) => `${item.name}: ${String(item.value)}`)
    .join(" · ") || "not reported";
}

export function inspectPacket(packet) {
  if (!object(packet) || !Array.isArray(packet.sources)) {
    throw new Error("Expected a Financial Evidence packet with a sources array.");
  }
  if (packet.schema !== "liquidity-lab.financial-evidence-packet.v1") {
    throw new Error("Unsupported or missing Financial Evidence packet schema.");
  }
  return {
    transport: token(packet.transport_status ?? packet.status, "unavailable"),
    evidence: token(packet.evidence_status, "not_evaluated"),
    carrier: token(packet.carrier_verification, "not_performed"),
    synthetic: packet.synthetic_example === true,
    sources: packet.sources.map((source) => ({
      product: token(source?.product, "Unknown product"),
      topic: token(source?.topic, "unknown-topic"),
      ok: source?.ok === true,
      carrier: token(source?.carrier_state, "not_reported"),
      states: formatReported(source?.source_reported?.state),
      clocks: formatReported(source?.source_reported?.clocks),
      error: token(source?.error, ""),
    })),
  };
}

function setText(selector, value) {
  const node = document.querySelector(selector);
  if (node) node.textContent = value;
}

function addLine(card, label, value) {
  const line = document.createElement("p");
  const name = document.createElement("b");
  name.textContent = `${label}: `;
  line.append(name, document.createTextNode(value));
  card.append(line);
}

function render(packet) {
  const view = inspectPacket(packet);
  document.querySelector("[data-results]").hidden = false;
  setText('[data-summary="transport"]', view.transport.replaceAll("_", " "));
  setText('[data-summary="evidence"]', view.evidence.replaceAll("_", " "));
  setText('[data-summary="carrier"]', view.carrier.replaceAll("_", " "));
  const target = document.querySelector("[data-sources]");
  target.replaceChildren();
  for (const source of view.sources) {
    const card = document.createElement("article");
    card.className = `source${source.ok ? "" : " bad"}`;
    const title = document.createElement("h3");
    title.textContent = source.product;
    card.append(title);
    addLine(card, "Topic", source.topic);
    addLine(card, "Retrieval", source.ok ? "succeeded" : "unavailable");
    addLine(card, "Source-reported state", source.states);
    addLine(card, "Source-reported clocks", source.clocks);
    addLine(card, "Carrier state", source.carrier);
    if (source.error) addLine(card, "Error", source.error);
    target.append(card);
  }
  setText("[data-status]", `${view.synthetic ? "Synthetic example" : "Local packet"}: ${view.sources.length} source records inspected. No file bytes were uploaded.`);
}

function clear() {
  const input = document.querySelector("[data-file]");
  if (input) input.value = "";
  document.querySelector("[data-results]").hidden = true;
  document.querySelector("[data-sources]").replaceChildren();
  setText("[data-status]", "No packet loaded.");
}

function bind() {
  const file = document.querySelector("[data-file]");
  if (!file) return;
  file.addEventListener("change", async () => {
    const selected = file.files?.[0];
    if (!selected) return;
    if (selected.size > 4_194_304) {
      setText("[data-status]", "The local file exceeds the 4 MiB inspector limit.");
      return;
    }
    try {
      render(JSON.parse(await selected.text()));
    } catch (error) {
      clear();
      setText("[data-status]", token(error?.message, "The local packet could not be read."));
    }
  });
  document.querySelector("[data-example]")?.addEventListener("click", () => render(SYNTHETIC_PACKET));
  document.querySelector("[data-clear]")?.addEventListener("click", clear);
}

if (typeof document !== "undefined") bind();
