from __future__ import annotations

import ast
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_workspace_and_runtime_mcp_tools_declare_titles():
    for rel in (
        "src/financial_evidence/workspace_mcp.py",
        "src/financial_evidence/runtime/mcp.py",
    ):
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"), filename=rel)
        tool_decs = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    if (
                        isinstance(dec, ast.Call)
                        and isinstance(dec.func, ast.Attribute)
                        and dec.func.attr == "tool"
                    ):
                        tool_decs += 1
                        kw = {k.arg: k.value for k in dec.keywords}
                        assert "title" in kw, f"{rel}:{node.name} missing tool title"
                        assert isinstance(kw["title"], ast.Constant) and isinstance(
                            kw["title"].value, str
                        )
                        assert kw["title"].value.strip()
        assert tool_decs > 0, f"no @server.tool decorators found in {rel}"


def test_colab_notebooks_are_valid_nbformat_and_python():
    nb_dir = ROOT / "notebooks"
    notebooks = sorted(nb_dir.glob("*.ipynb"))
    assert len(notebooks) == 4
    for nb_path in notebooks:
        nb = json.loads(nb_path.read_text(encoding="utf-8"))
        assert nb["nbformat"] == 4
        code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
        assert code_cells, f"{nb_path.name} has no code cells"
        for cell in code_cells:
            src = "".join(cell["source"])
            ast.parse(src, filename=nb_path.name)


def test_framework_quickstarts_parse_cleanly():
    fw_dir = ROOT / "examples" / "frameworks"
    py_files = sorted(fw_dir.glob("*.py"))
    assert len(py_files) == 4
    for path in py_files:
        ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
    assert (fw_dir / "README.md").is_file()


def test_floss_funding_manifest_is_valid():
    data = json.loads((ROOT / "funding.json").read_text(encoding="utf-8"))
    assert data["version"] == "v1.0.0"
    assert data["entity"]["name"] == "LIQUILENS PRIVATE LIMITED"
    assert len(data["projects"]) >= 3
    assert data["funding"]["channels"]
    assert data["funding"]["plans"]
