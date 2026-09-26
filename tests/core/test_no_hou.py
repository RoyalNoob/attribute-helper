import ast
from pathlib import Path

CORE = Path(__file__).parents[2] / "python" / "attribute_helper" / "core"


def test_core_does_not_import_hou():
    offenders = []
    for path in CORE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            if any(n == "hou" or n.startswith("hou.") for n in names):
                offenders.append(f"{path.name}:{node.lineno}")
    assert not offenders, f"core/ imports hou: {offenders}"
