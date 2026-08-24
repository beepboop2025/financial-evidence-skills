"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

require("../docs/integrations/fdc3/evidence-inspector/app.js");

const runtime = globalThis.FinancialEvidenceFdc3;

function fakeDocument() {
  const ids = [
    "broadcast-button",
    "composer-message",
    "context-input",
    "context-received-at",
    "context-source",
    "context-transport",
    "context-type",
    "fdc3-status",
    "fdc3-status-detail",
    "fdc3-status-indicator",
    "load-example-button",
    "received-context",
  ];
  const elements = Object.fromEntries(
    ids.map((id) => [
      id,
      {
        className: "",
        listeners: {},
        textContent: "",
        value: "",
        addEventListener(type, handler) {
          this.listeners[type] = handler;
        },
      },
    ]),
  );
  return {
    elements,
    getElementById(id) {
      return elements[id] || null;
    },
  };
}

test("context validation accepts only the three declared standard types", () => {
  assert.deepEqual(runtime.SUPPORTED_CONTEXT_TYPES, [
    "fdc3.instrument",
    "fdc3.organization",
    "fdc3.country",
  ]);
  assert.equal(
    runtime.parseContext('{"type":"fdc3.instrument","id":{"ticker":"AAPL"}}').type,
    "fdc3.instrument",
  );
  assert.throws(() => runtime.parseContext("not json"), /valid JSON/);
  assert.throws(
    () => runtime.validateContext({ type: "fdc3.order" }),
    /Unsupported context type/,
  );
});

test("runtime registers matching FDC3 listeners and broadcasts unchanged context", async () => {
  const document = fakeDocument();
  const contextHandlers = new Map();
  const intents = [];
  const broadcasts = [];
  const api = {
    async addContextListener(type, handler) {
      contextHandlers.set(type, handler);
      return { unsubscribe() {} };
    },
    async addIntentListener(intent, handler) {
      intents.push({ intent, handler });
      return { unsubscribe() {} };
    },
    async broadcast(context) {
      broadcasts.push(context);
    },
  };
  const inspector = runtime.createInspector({
    window: { addEventListener() {} },
    document,
    now: () => new Date("2026-08-24T12:00:00Z"),
  });

  await inspector.connect(api);
  assert.deepEqual([...contextHandlers.keys()], runtime.SUPPORTED_CONTEXT_TYPES);
  assert.deepEqual(intents.map(({ intent }) => intent), ["ViewInstrument"]);
  assert.match(document.elements["fdc3-status"].textContent, /connected/);

  const incoming = { type: "fdc3.organization", id: { LEI: "example-lei" } };
  contextHandlers.get("fdc3.organization")(incoming, {
    source: { appId: "source-app", instanceId: "instance-1" },
  });
  assert.equal(document.elements["context-type"].textContent, "fdc3.organization");
  assert.equal(document.elements["context-source"].textContent, "source-app (instance-1)");
  assert.equal(document.elements["context-received-at"].textContent, "2026-08-24T12:00:00.000Z");
  assert.deepEqual(JSON.parse(document.elements["received-context"].textContent), incoming);

  const outgoing = { type: "fdc3.country", name: "India", id: { ISOALPHA2: "IN" } };
  document.elements["context-input"].value = JSON.stringify(outgoing);
  assert.equal(await inspector.broadcastInput(), true);
  assert.deepEqual(broadcasts, [outgoing]);
  assert.match(document.elements["composer-message"].textContent, /broadcast unchanged/);
});

test("AppD declaration and runtime expose the same contexts and intent", () => {
  const record = JSON.parse(
    fs.readFileSync(path.join(__dirname, "../integrations/fdc3/appd-record.json"), "utf8"),
  );
  assert.equal(record.name, "financial-evidence-inspector");
  assert.equal(
    record.details.url,
    "https://beepboop2025.github.io/financial-evidence-skills/integrations/fdc3/evidence-inspector/",
  );
  assert.deepEqual(record.interop.userChannels.listensFor, runtime.SUPPORTED_CONTEXT_TYPES);
  assert.deepEqual(record.interop.userChannels.broadcasts, runtime.SUPPORTED_CONTEXT_TYPES);
  assert.deepEqual(Object.keys(record.interop.intents.listensFor), ["ViewInstrument"]);
  assert.deepEqual(record.interop.intents.listensFor.ViewInstrument.contexts, [
    "fdc3.instrument",
  ]);
  assert.equal(Object.hasOwn(record, "publisher"), false);
});
