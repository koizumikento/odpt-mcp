import asyncio
import json
import sys
from argparse import SUPPRESS, ArgumentParser
from collections.abc import Sequence

import httpx

from .client import search_railway


def run_cli(argv: Sequence[str]) -> None:
    parser = ArgumentParser(prog="odpt-mcp")
    commands = parser.add_subparsers(required=True)

    command = commands.add_parser("search-railway", argument_default=SUPPRESS)
    command.add_argument("--kind", choices=("station", "line"), required=True)
    command.add_argument("--query")
    command.add_argument("--limit", type=int)
    command.set_defaults(handler=search_railway)

    arguments = vars(parser.parse_args(argv))
    handler = arguments.pop("handler")
    try:
        result = asyncio.run(handler(**arguments))
    except (ValueError, OSError, httpx.HTTPError) as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8"))
