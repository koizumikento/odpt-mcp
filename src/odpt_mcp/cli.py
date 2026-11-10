import asyncio
import json
import sys
from argparse import SUPPRESS, ArgumentParser
from collections.abc import Sequence

import httpx

from . import client


def _add_pagination(command: ArgumentParser) -> None:
    command.add_argument("--limit", type=int)
    command.add_argument("--offset", type=int)


def run_cli(argv: Sequence[str]) -> None:
    parser = ArgumentParser(prog="odpt-mcp")
    commands = parser.add_subparsers(required=True)

    command = commands.add_parser("search-railway", argument_default=SUPPRESS)
    command.add_argument("--kind", choices=("station", "line"), required=True)
    command.add_argument("--query")
    command.add_argument("--limit", type=int)
    command.set_defaults(handler=client.search_railway)

    command = commands.add_parser("get-station-timetable", argument_default=SUPPRESS)
    command.add_argument("--station-id", required=True)
    command.add_argument("--calendar-id")
    command.add_argument("--direction-id")
    _add_pagination(command)
    command.set_defaults(handler=client.get_station_timetable)

    command = commands.add_parser("get-train-status", argument_default=SUPPRESS)
    command.add_argument("--line-id")
    command.set_defaults(handler=client.get_train_status)

    command = commands.add_parser("get-railway-fare", argument_default=SUPPRESS)
    command.add_argument("--from-station-id", required=True)
    command.add_argument("--to-station-id", required=True)
    command.set_defaults(handler=client.get_railway_fare)

    command = commands.add_parser("search-bus-stops", argument_default=SUPPRESS)
    command.add_argument("--name", required=True)
    _add_pagination(command)
    command.set_defaults(handler=client.search_bus_stops)

    command = commands.add_parser("get-bus-stop-timetable", argument_default=SUPPRESS)
    command.add_argument("--stop-id", required=True)
    command.add_argument("--calendar-id")
    command.add_argument("--route-id")
    _add_pagination(command)
    command.set_defaults(handler=client.get_bus_stop_timetable)

    command = commands.add_parser("get-bus-route", argument_default=SUPPRESS)
    command.add_argument("--pattern-id", required=True)
    _add_pagination(command)
    command.set_defaults(handler=client.get_bus_route)

    command = commands.add_parser("get-bus-fare", argument_default=SUPPRESS)
    command.add_argument("--pattern-id", required=True)
    command.add_argument("--from-stop-id", required=True)
    command.add_argument("--to-stop-id", required=True)
    command.set_defaults(handler=client.get_bus_fare)

    arguments = vars(parser.parse_args(argv))
    handler = arguments.pop("handler")
    try:
        result = asyncio.run(handler(**arguments))
    except (ValueError, OSError, httpx.HTTPError) as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8"))
