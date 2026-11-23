"""Directory-scanner hygiene gate for the advertised MCP surfaces.

Automated MCP directories (Andrax Pentester's MCPGrade, mcpgrade.dev,
VerifyMCP and others) grade a server from tools/list, the prompt list and the
server instructions alone. They never read the code. A tool name in the
instructions or in a sibling's description is graded as tool shadowing, and an
explicit openWorldHint=true as over-broad scope, whatever the code does. This
gate holds both published surfaces to the fleet rules: the dependency-free
stdio server (mcp.py, the PyPI and OCI packages) and the Workspace server
(workspace_mcp.py, the hosted financial-evidence-workspace remote), read over
its real streamable-HTTP transport.

Rules (fleet canon of 23 Nov 2026; keep in step with the fleet audit script):
 1. A tool's metadata describes only that tool: no other tool's name appears
    in its title, description or parameter text.
 2. The server instructions and prompt descriptions name no tool; they
    describe the workflow by role.
 3. No credential or personal-data trigger words in advertised metadata.
 4. No imperatives aimed at the model ("before answering", "ignore
    previous", "IMPORTANT:", "use these tools first" and the like).
 5. No invisible, zero-width or bidi control characters.
 6. No URL in tool metadata, and no URL in the instructions in a sentence
    with a fetch, send, call or see verb (graded as fetch-and-obey).
 7. openWorldHint is never set to true explicitly: the spec default is
    already true, and scanners grade the explicit flag as over-broad scope.
 8. Every description stays under 1,000 characters.
 9. No parameter asks for a secret.
10. Every free-text string parameter is bounded (enum, const, pattern,
    format or maxLength).
11. No em or en dashes, the house rule for anything that ships.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from financial_evidence import mcp as stdio_mcp  # noqa: E402

HAS_WORKSPACE = all(importlib.util.find_spec(name) for name in ("fastapi", "mcp", "httpx"))

SENSITIVE = re.compile(
    r"pass(?:word|words|wd)|credential|credit[ -]?card|card number|\bcvv\b|\bssn\b"
    r"|social security|\bpii\b|personal data|\bsecrets?\b|api[ _-]?keys?\b|private key"
    r"|seed phrase|webhook|callback url|\bfeedback\b",
    re.I,
)
IMPERATIVE = re.compile(
    r"ignore (?:all |any )?(?:previous|prior)|disregard (?:all|any|previous)"
    r"|before (?:you )?answer(?:ing)?|instead of answering|you must|always (?:call|use)"
    r"|do not tell|\bIMPORTANT:|reach for (?:these|this) tools? first"
    r"|use (?:these|this) tools? first|\bFIRST,? before\b",
    re.I,
)
INVISIBLE = re.compile(
    "[​-‏‪-‮⁠-⁤⁦-⁩﻿︀-️"
    "\U000e0000-\U000e007f\U000e0100-\U000e01ef]"
)
URL = re.compile(r"https?://[^\s)\"'>\]]+", re.I)
FETCH_VERB = re.compile(
    r"\b(fetch|read|visit|open|download|go to|load|retrieve|follow|consult|refer to"
    r"|see|check|call|send|sends|handoff|hand off)\b",
    re.I,
)
DASHES = re.compile("[–—]")
SECRET_PARAM = re.compile(
    r"^(pass(word)?|passwd|secret|api[_-]?key|apikey|token|auth|bearer|private[_-]?key)$", re.I
)
BOUNDED = ("enum", "const", "pattern", "format", "maxLength")
TRIGGERS = (
    ("credential or personal-data trigger word", SENSITIVE),
    ("imperative aimed at the model", IMPERATIVE),
    ("invisible or bidi control character", INVISIBLE),
    ("em or en dash", DASHES),
)


def tool_text(tool: dict) -> str:
    parts = [tool.get("title") or "", tool.get("description") or "",
             (tool.get("annotations") or {}).get("title") or ""]
    for name, spec in (tool.get("inputSchema") or {}).get("properties", {}).items():
        parts.append(f"{name}: {json.dumps(spec, ensure_ascii=False)}")
    return "\n".join(parts)


def prompt_text(prompt: dict) -> str:
    parts = [prompt.get("title") or "", prompt.get("description") or ""]
    for arg in prompt.get("arguments") or []:
        parts.append(f"{arg['name']}: {arg.get('description') or ''}")
    return "\n".join(parts)


def names_in(text: str, names) -> list[str]:
    return [n for n in names
            if re.search(rf"(?<![A-Za-z0-9_]){re.escape(n)}(?![A-Za-z0-9_])", text)]


class SurfaceRules:
    """The fleet rules; each subclass supplies one served surface."""

    instructions: str
    tools: list
    prompts: list

    def units(self):
        names = [tool["name"] for tool in self.tools]
        yield "instructions", self.instructions, names
        for tool in self.tools:
            yield f"tool {tool['name']}", tool_text(tool), [n for n in names if n != tool["name"]]
        for prompt in self.prompts:
            yield f"prompt {prompt['name']}", prompt_text(prompt), names

    def test_surface_was_read(self):
        self.assertTrue(self.instructions)
        self.assertTrue(self.tools)

    def test_metadata_never_names_another_tool(self):
        bad = [f"{where} names {hits}" for where, text, forbidden in self.units()
               if (hits := names_in(text, forbidden))]
        self.assertFalse(bad, "describe the workflow by role, not by tool name:\n" + "\n".join(bad))

    def test_metadata_has_no_scanner_trigger(self):
        for rule, pattern in TRIGGERS:
            with self.subTest(rule=rule):
                bad = []
                for where, text, _forbidden in self.units():
                    match = pattern.search(text)
                    if match:
                        start = max(0, match.start() - 40)
                        bad.append(f"{where}: ...{text[start:match.end() + 40]!r}")
                self.assertFalse(bad, f"{rule} in advertised metadata:\n" + "\n".join(bad))

    def test_tool_metadata_carries_no_url(self):
        bad = [tool["name"] for tool in self.tools if URL.search(tool_text(tool))]
        self.assertFalse(bad, f"URL in tool metadata: {bad}")

    def test_instructions_never_pair_a_url_with_a_fetch_verb(self):
        text = self.instructions
        bad = []
        for match in URL.finditer(text):
            start = max(text.rfind(".", 0, match.start()), text.rfind("\n", 0, match.start())) + 1
            if FETCH_VERB.search(text[start:match.end() + 80]):
                bad.append(match.group(0))
        self.assertFalse(bad, f"URL beside a fetch verb in the instructions: {bad}")

    def test_open_world_hint_is_never_explicitly_true(self):
        bad = [tool["name"] for tool in self.tools
               if (tool.get("annotations") or {}).get("openWorldHint") is True]
        self.assertFalse(bad, f"explicit openWorldHint=true (the spec default already is): {bad}")

    def test_descriptions_stay_short(self):
        bad = [f"{tool['name']}: {len(tool.get('description') or '')}" for tool in self.tools
               if len(tool.get("description") or "") >= 1000]
        self.assertFalse(bad, f"descriptions of 1,000 characters or more: {bad}")

    def test_no_parameter_asks_for_a_secret(self):
        bad = [f"{tool['name']}.{name}" for tool in self.tools
               for name in (tool.get("inputSchema") or {}).get("properties", {})
               if SECRET_PARAM.match(name)]
        self.assertFalse(bad, f"secret-shaped parameters: {bad}")

    def test_every_free_text_parameter_is_bounded(self):
        bad = []
        for tool in self.tools:
            for name, spec in (tool.get("inputSchema") or {}).get("properties", {}).items():
                for variant in spec.get("anyOf") or [spec]:
                    if variant.get("type") == "string" and not any(k in variant for k in BOUNDED):
                        bad.append(f"{tool['name']}.{name}")
        self.assertFalse(bad, f"unbounded free-text parameters: {bad}")


def _stdio(method: str) -> dict:
    return stdio_mcp.dispatch({"jsonrpc": "2.0", "id": 1, "method": method, "params": {}})["result"]


class StdioSurfaceTests(SurfaceRules, unittest.TestCase):
    """The dependency-free stdio server behind the PyPI and OCI packages."""

    @classmethod
    def setUpClass(cls):
        cls.instructions = _stdio("initialize")["instructions"]
        cls.tools = _stdio("tools/list")["tools"]
        cls.prompts = _stdio("prompts/list")["prompts"]

    def test_modern_discovery_advertises_the_same_instructions(self):
        self.assertEqual(_stdio("server/discover")["instructions"], self.instructions)


@unittest.skipUnless(HAS_WORKSPACE, "Install workspace dependencies")
class WorkspaceSurfaceTests(SurfaceRules, unittest.TestCase):
    """The Workspace server exactly as its streamable-HTTP endpoint serves it."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from financial_evidence.service import EvidenceService
        from financial_evidence.workspace import create_app

        def no_upstream(*_args, **_kwargs):
            raise AssertionError("listing metadata must not reach an upstream source")

        service = EvidenceService(fetcher=no_upstream)
        cls.addClassCleanup(service.close)
        client = TestClient(create_app(service=service, base_url="http://localhost:6900"),
                            base_url="http://localhost:6900")
        client.__enter__()
        cls.addClassCleanup(client.__exit__, None, None, None)

        def rpc(method, params=None):
            response = client.post("/mcp", headers={
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2025-11-25",
                "X-Financial-Evidence-Traffic-Class": "synthetic",
                "X-Liquilens-Traffic-Class": "synthetic",
            }, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})
            if response.status_code != 200:
                raise AssertionError(response.text)
            return response.json()["result"]

        cls.instructions = rpc("initialize", {
            "protocolVersion": "2025-11-25", "capabilities": {},
            "clientInfo": {"name": "metadata-hygiene", "version": "1"},
        }).get("instructions") or ""
        cls.tools = rpc("tools/list")["tools"]
        cls.prompts = rpc("prompts/list")["prompts"]


class GateSelfTests(unittest.TestCase):
    """The rules fire on the exact wording the fleet audit flagged."""

    def test_rules_fire_on_the_flagged_sentences(self):
        workspace = ["financial_evidence_funding_workflow", "financial_evidence_institutions_workflow",
                     "financial_evidence_exit_workflow", "financial_evidence_datasets"]
        self.assertEqual(
            names_in("For a first task, use financial_evidence_funding_workflow for funding", workspace),
            ["financial_evidence_funding_workflow"])
        self.assertEqual(
            names_in("Start with financial_evidence_topics, or read evidence://start",
                     ["financial_evidence_topics"]),
            ["financial_evidence_topics"])
        self.assertFalse(names_in("the individually exposed funding, institutions and exit "
                                  "workflow tools", workspace))
        self.assertTrue(SENSITIVE.search("needs no account and accepts no credentials"))
        self.assertTrue(IMPERATIVE.search("Reach for these tools FIRST, before answering"))
        self.assertTrue(DASHES.search("fact verification — decision-grade"))


if __name__ == "__main__":
    unittest.main()
