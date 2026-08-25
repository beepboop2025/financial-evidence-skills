"use strict";

const assert = require("node:assert/strict");
const { readFile } = require("node:fs/promises");
const test = require("node:test");

let inspectPacket;
test.before(async () => {
  ({ inspectPacket } = await import("../integrations/huggingface-space/app.mjs"));
});


test("Space inspector keeps transport, evidence, and carrier states separate", () => {
  const view = inspectPacket({
    schema: "liquidity-lab.financial-evidence-packet.v1",
    status: "complete",
    transport_status: "complete",
    evidence_status: "not_evaluated",
    carrier_verification: "not_performed",
    sources: [
      {
        product: "Seiche",
        topic: "money-market",
        ok: true,
        carrier_state: "not_published",
        source_reported: {
          state: [{ name: "response_status", value: "PARTIAL" }],
          clocks: "not_reported",
        },
      },
    ],
  });
  assert.equal(view.transport, "complete");
  assert.equal(view.evidence, "not_evaluated");
  assert.equal(view.carrier, "not_performed");
  assert.equal(view.sources[0].states, "response_status: PARTIAL");
  assert.equal(view.sources[0].clocks, "not_reported");
});


test("legacy and malformed packets fail closed", () => {
  const legacy = inspectPacket({
    schema: "liquidity-lab.financial-evidence-packet.v1",
    status: "complete",
    sources: [],
  });
  assert.equal(legacy.evidence, "not_evaluated");
  assert.equal(legacy.carrier, "not_performed");
  assert.throws(() => inspectPacket({ status: "complete", sources: [] }), /schema/);
  assert.throws(() => inspectPacket({ schema: "other" }), /sources array/);
});


test("static Space has no network or unsafe evidence rendering path", async () => {
  const root = new URL("../integrations/huggingface-space/", `file://${__filename}`);
  const [html, script, readme] = await Promise.all([
    readFile(new URL("index.html", root), "utf8"),
    readFile(new URL("app.mjs", root), "utf8"),
    readFile(new URL("README.md", root), "utf8"),
  ]);
  assert.match(html, /connect-src 'none'/);
  assert.match(html, /uploads nothing/);
  assert.doesNotMatch(html, /cloudflareinsights|google-analytics|plausible\.io/i);
  assert.doesNotMatch(script, /\bfetch\s*\(/);
  assert.doesNotMatch(script, /\.innerHTML\s*=/);
  assert.match(script, /textContent =/);
  assert.match(readme, /^---\n[\s\S]*sdk: static[\s\S]*app_file: index\.html[\s\S]*\n---/);
  assert.match(readme, /synthetic and deliberately/);
  assert.match(readme, /license: mit/);
  assert.match(html, /MIT-licensed source/);
});
