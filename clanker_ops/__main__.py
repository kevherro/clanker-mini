"""JSON CLI for the optional local operations toolkit."""

import argparse
import json
from pathlib import Path
import sqlite3
import sys

from . import resources, work
from .store import Store


def operations():
    return {**work.OPS, **resources.OPS}


def initialize(store):
    work.initialize(store)
    resources.initialize(store)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("JSON must contain finite numbers")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True, type=Path,
                        help="Shared authority directory on this host's local disk")
    parser.add_argument("--input", default="-", help="JSON file, or - for standard input")
    parser.add_argument("operation", choices=sorted(operations()))
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text()
        request = json.loads(raw, object_pairs_hook=unique_object,
                             parse_constant=reject_constant)
        if not isinstance(request, dict):
            raise ValueError("Input must be a JSON object")
        with Store(args.store) as store:
            initialize(store)
            result = operations()[args.operation](store, request)
        print(json.dumps(result, allow_nan=False, sort_keys=True))
        if args.operation == "resource-reap" and (
                result.get("pass_exhausted") or any(row.get("last_error") for row in result["reservations"])):
            return 2
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
