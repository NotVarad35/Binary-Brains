"""Static check: every relative import in frontend/src resolves to a real file.

Run from repo root:  python scripts/check_frontend_imports.py
(Only stdlib, so it works without Node installed.)
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "frontend" / "src"

# import ... from "./x"  /  import "./x"  /  export ... from "./x"
IMPORT_RE = re.compile(
    r"""(?:import|export)\b[^'"]*?['"](\.{1,2}/[^'"]+)['"]""",
    re.DOTALL,
)
# Strip comments so doc examples (e.g. `import { BASE_URL } from "../apiConfig"`
# inside a JSDoc block) are not mistaken for real imports.
BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
LINE_COMMENT_RE = re.compile(r"//[^\n]*")
EXTENSIONS = [".jsx", ".js", ".ts", ".tsx", ".css", ".json", ""]


def strip_comments(text: str) -> str:
    """Remove comments, preserving line numbers (replace with blanks)."""
    text = BLOCK_COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    text = LINE_COMMENT_RE.sub("", text)
    return text


def resolve(spec: str, from_file: Path) -> Path | None:
    base = (from_file.parent / spec).resolve()
    for ext in EXTENSIONS:
        candidate = Path(str(base) + ext) if ext else base
        if candidate.is_file():
            return candidate
    # directory import -> index file
    for ext in EXTENSIONS:
        if ext and (base / f"index{ext}").is_file():
            return base / f"index{ext}"
    return None


def main() -> int:
    if not SRC.is_dir():
        print(f"missing {SRC}")
        return 1

    files = sorted(p for p in SRC.rglob("*") if p.suffix in {".js", ".jsx", ".ts", ".tsx"})
    missing = 0
    checked = 0

    for f in files:
        text = strip_comments(f.read_text(encoding="utf-8"))
        for spec in IMPORT_RE.findall(text):
            checked += 1
            if resolve(spec, f) is None:
                missing += 1
                print(f"UNRESOLVED  {f.relative_to(ROOT)}  ->  {spec}")

    print(f"files: {len(files)}   relative imports checked: {checked}   unresolved: {missing}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
