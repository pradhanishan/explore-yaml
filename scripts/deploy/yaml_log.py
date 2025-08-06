#!/usr/bin/env python3
"""
YAML Inspector (emoji-safe truncation)

Finds your project root via a `.root` marker, then
locates every .yaml/.yml under it. For each file it
loads via ruamel.yaml, flattens all scalar values,
and prints a per-file table:

  File | Location   | Key Path | Value                  | Type

Long strings (including emojis) are truncated
to a fixed display width so cells never wrap.
"""

import sys
from pathlib import Path
from typing import Any, Iterator, List, Tuple, Union

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from tabulate import tabulate
from wcwidth import wcswidth

yaml_loader = YAML(typ="safe")
MAX_VALUE_WIDTH = 60  # display columns


def find_project_root(marker: str = ".root") -> Path:
    start = Path.cwd().resolve()
    for d in (start, *start.parents):
        if (d / marker).is_file():
            return d
    sys.exit(f"Error: marker '{marker}' not found from {start} upward")


def find_yaml_files(root: Path) -> Iterator[Path]:
    yield from root.rglob("*.yaml")
    yield from root.rglob("*.yml")


def read_yaml(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml_loader.load(f) or {}
    except YAMLError as e:
        sys.exit(f"Error parsing YAML at {path}: {e}")


def flatten(
    obj: Any,
    path: List[Union[str, int]] = None # type: ignore
) -> Iterator[Tuple[List[Union[str, int]], Any]]:
    stack: List[Tuple[Any, List[Union[str, int]]]] = [(obj, path or [])]
    while stack:
        node, pth = stack.pop()
        if isinstance(node, dict):
            for k, v in node.items():
                stack.append((v, pth + [k]))
        elif isinstance(node, list):
            for i, item in enumerate(node):
                stack.append((item, pth + [i]))
        else:
            yield pth, node


def truncate_display(s: str, max_width: int = MAX_VALUE_WIDTH) -> str:
    """
    Truncate `s` so its terminal display width ≤ max_width,
    respecting wide chars (including emojis).
    """
    if wcswidth(s) <= max_width:
        return s
    out = ""
    width = 0
    for ch in s:
        w = wcswidth(ch)
        if width + w > max_width - 3:
            out += "..."
            break
        out += ch
        width += w
    return out


def tabulate_file(path: Path, project_root: Path):
    data = read_yaml(path)
    rows: List[List[Any]] = []

    for key_path, value in flatten(data):
        key_str = ".".join(str(e) for e in key_path) or "(root)"
        val_str = truncate_display(str(value))
        rows.append([
            path.name,
            str(path.relative_to(project_root)),
            key_str,
            val_str,
            type(value).__name__,
        ])

    print(f"\n=== {path.relative_to(project_root)} ===")
    print(tabulate(
        rows,
        headers=["File", "Location", "Key Path", "Value", "Type"],
        tablefmt="fancy_grid",
        stralign="left"
    ))


def main():
    root = find_project_root()
    files = sorted(find_yaml_files(root))
    if not files:
        sys.exit("No YAML files found under project root.")
    for yf in files:
        tabulate_file(yf, root)


if __name__ == "__main__":
    main()
