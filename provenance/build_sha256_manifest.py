"""Build or verify the canonical, cross-platform SHA-256 manifest."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "provenance" / "SHA256SUMS.txt"
BINARY_SUFFIXES = {
    ".ckpt",
    ".jpeg",
    ".jpg",
    ".pdf",
    ".png",
    ".safetensors",
    ".wav",
    ".xlsx",
}


def canonical_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    if path.suffix.casefold() in BINARY_SUFFIXES:
        return raw
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def entries() -> list[tuple[str, str]]:
    result = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.parts or path == MANIFEST:
            continue
        relative = path.relative_to(ROOT).as_posix()
        digest = hashlib.sha256(canonical_bytes(path)).hexdigest()
        result.append((digest, relative))
    return result


def render(items: list[tuple[str, str]]) -> str:
    return "".join(f"{digest}  {path}\n" for digest, path in items)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render(entries())
    if args.check:
        actual = MANIFEST.read_text(encoding="utf-8").replace("\r\n", "\n")
        if actual != expected:
            raise SystemExit("SHA256SUMS.txt is stale or invalid")
        print(f"PASS: {len(entries())} canonical files verified")
        return 0
    MANIFEST.write_text(expected, encoding="utf-8", newline="\n")
    print(f"Wrote {len(entries())} canonical hashes to {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
