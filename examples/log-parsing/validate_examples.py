#!/usr/bin/env python3
"""
validate_examples.py — Run every documented log-parsing example against the local testers.

Walks the per-recipe directories (<category>/<recipe>/README.md), extracts the
validation fixture declared after `<!-- validation: kind=... -->`, runs it
through dissect_tester.py / grok_tester.py / relabel_tester.py, and reports
PASS / FAIL. This validates that the config snippets in the Kloudfuse log
parsing documentation produce the facets/labels they claim to — entirely
locally, with no Kloudfuse cluster required.

Usage:
    python3 validate_examples.py
    python3 validate_examples.py --only grammar/dissect-nginx-access-log
    python3 validate_examples.py --only relabel
"""

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from dissect_tester import dissect, DissectError  # noqa: E402
from relabel_tester import apply_action, DroppedError  # noqa: E402

try:
    from pygrok import Grok
except ImportError:
    Grok = None

_MARKER_RE = re.compile(r"<!--\s*validation:\s*kind=(\w+)\s*-->")
_BLOCK_RE = re.compile(r"```json\n(.*?)\n```", re.DOTALL)


def parse_readme(path: Path):
    text = path.read_text(encoding="utf-8")
    marker = _MARKER_RE.search(text)
    if not marker:
        return None, None
    block = _BLOCK_RE.search(text, marker.end())
    if not block:
        return None, None
    return marker.group(1), json.loads(block.group(1))


def run_dissect(spec):
    result = dissect(spec["tokenizer"], spec["line"])
    return result == spec["expected"], result


def run_grok(spec):
    if Grok is None:
        return None, "pygrok not installed — pip install pygrok"
    combined = "".join(spec["patterns"])
    grok = Grok(combined)
    result = grok.match(spec["line"])
    if result is None:
        return False, "pattern did not match"
    return result == spec["expected"], result


def run_relabel(spec):
    try:
        facets, labels = apply_action(spec["args"], spec["input"].get("facets", {}),
                                       spec["input"].get("labels", {}))
    except DroppedError:
        ok = spec["expected"].get("dropped") is True
        return ok, {"dropped": True}
    result = {"facets": facets, "labels": labels}
    return result == spec["expected"], result


RUNNERS = {"dissect": run_dissect, "grok": run_grok, "relabel": run_relabel}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help="Only run recipes under this category/recipe path")
    args = parser.parse_args()

    readmes = sorted(HERE.glob("*/*/README.md"))
    if args.only:
        readmes = [r for r in readmes if args.only in str(r.relative_to(HERE))]

    passed = failed = skipped = 0
    for readme in readmes:
        label = str(readme.relative_to(HERE).parent)
        kind, spec = parse_readme(readme)
        if kind is None:
            continue
        runner = RUNNERS.get(kind)
        if runner is None:
            print(f"SKIP  {label}  (unknown kind={kind})")
            skipped += 1
            continue
        try:
            ok, detail = runner(spec)
        except (DissectError, Exception) as e:  # noqa: BLE001 — surface any tester failure as FAIL
            print(f"FAIL  {label}  ({e})")
            failed += 1
            continue
        if ok is None:
            print(f"SKIP  {label}  ({detail})")
            skipped += 1
        elif ok:
            print(f"PASS  {label}")
            passed += 1
        else:
            print(f"FAIL  {label}  got={detail}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
