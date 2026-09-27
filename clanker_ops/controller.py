"""Run expiry reconciliation independently of an agent, under a real supervisor."""

import argparse
import json
import math
import os
from pathlib import Path
import signal
import sqlite3
import sys
import threading

from . import resources
from .store import Store


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True, type=Path)
    parser.add_argument("--adapter", required=True, type=Path)
    parser.add_argument("--interval", type=float, default=15,
                        help="Seconds between reconciliation passes")
    parser.add_argument("--timeout", type=float, default=10,
                        help="Total seconds allowed for each reconciliation pass (at most 60)")
    parser.add_argument("--once", action="store_true", help="One pass, suitable for a scheduler")
    args = parser.parse_args(argv)
    if not math.isfinite(args.interval) or args.interval <= 0:
        parser.error("interval must be finite and positive")
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 60:
        parser.error("timeout must be positive and at most 60 seconds")
    if (not args.adapter.is_absolute() or not args.adapter.is_file()
            or not os.access(args.adapter, os.X_OK)):
        parser.error("adapter must name an existing absolute executable path")
    stop = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    with Store(args.store) as store:
        resources.initialize(store)
        while not stop.is_set():
            try:
                result = resources.OPS["resource-reap"](
                    store, {"adapter": str(args.adapter), "timeout": args.timeout})
                print(json.dumps(result, allow_nan=False, sort_keys=True), flush=True)
                if args.once and (result.get("pass_exhausted") or
                                  any(row.get("last_error") for row in result["reservations"])):
                    return 2
            except (ValueError, OSError, sqlite3.Error) as exc:
                print(json.dumps({"error": str(exc)}), file=sys.stderr, flush=True)
                if args.once:
                    return 2
            if args.once or stop.wait(args.interval):
                break
    return 0


if __name__ == "__main__":
    sys.exit(main())
