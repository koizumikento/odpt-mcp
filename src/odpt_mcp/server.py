from collections.abc import Awaitable, Callable
from functools import wraps

import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from . import client

READ_ONLY = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True, destructive_hint=False, open_world_hint=True
)


def _tool_errors[**P, R](function: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    @wraps(function)
    async def invoke(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await function(*args, **kwargs)
        except (ValueError, OSError, httpx.HTTPError) as exc:
            raise ToolError(str(exc)) from None

    return invoke


def create_server() -> MCPServer:
    mcp = MCPServer("odpt-mcp")
    register = mcp.tool(annotations=READ_ONLY)
    register(_tool_errors(client.search_railway))
    register(_tool_errors(client.get_station_timetable))
    register(_tool_errors(client.get_train_status))
    register(_tool_errors(client.get_railway_fare))
    register(_tool_errors(client.search_bus_stops))
    register(_tool_errors(client.get_bus_stop_timetable))
    register(_tool_errors(client.get_bus_route))
    register(_tool_errors(client.get_bus_fare))
    return mcp
