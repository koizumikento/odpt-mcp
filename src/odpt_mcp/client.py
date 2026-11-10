from typing import Annotated, Any, Literal

import httpx
from pydantic import Field, validate_call

BASE_URL = "https://api-public.odpt.org/api/v4/"
OPERATOR = "odpt.Operator:Toei"
DATASETS = {
    "station": "https://ckan.odpt.org/dataset/r_station-toei",
    "line": "https://ckan.odpt.org/dataset/r_route-toei",
    "station_timetable": "https://ckan.odpt.org/dataset/r_station_timetable-toei",
    "train_status": "https://ckan.odpt.org/dataset/r_train_status-toei",
    "railway_fare": "https://ckan.odpt.org/dataset/r_fare-toei",
    "bus_stop": "https://ckan.odpt.org/dataset/b_busstop-toei",
    "bus_stop_timetable": "https://ckan.odpt.org/dataset/b_busstop_timetable-toei",
    "bus_fare": "https://ckan.odpt.org/dataset/b_busfare-toei",
    "bus_route": "https://ckan.odpt.org/dataset/b_busroute-toei",
}
Query = Annotated[str, Field(min_length=1, max_length=100, pattern=r"\S")]
Limit = Annotated[int, Field(ge=1, le=50)]
Offset = Annotated[int, Field(ge=0)]
StationID = Annotated[str, Field(max_length=200, pattern=r"^odpt\.Station:Toei\.[A-Za-z0-9_.-]+$")]
LineID = Annotated[str, Field(max_length=200, pattern=r"^odpt\.Railway:Toei\.[A-Za-z0-9_.-]+$")]
CalendarID = Annotated[str, Field(max_length=200, pattern=r"^odpt\.Calendar:[A-Za-z0-9_.-]+$")]
DirectionID = Annotated[
    str, Field(max_length=200, pattern=r"^odpt\.RailDirection:[A-Za-z0-9_.-]+$")
]
BusStopID = Annotated[
    str, Field(max_length=200, pattern=r"^odpt\.BusstopPole:Toei\.[A-Za-z0-9_.-]+$")
]
BusRouteID = Annotated[
    str, Field(max_length=200, pattern=r"^odpt\.Busroute:Toei\.[A-Za-z0-9_.-]+$")
]
BusPatternID = Annotated[
    str, Field(max_length=200, pattern=r"^odpt\.BusroutePattern:Toei\.[A-Za-z0-9_.-]+$")
]

type Row = dict[str, Any]


async def _fetch_rows(resource: str, filters: dict[str, str] | None = None) -> list[Row]:
    params = {"odpt:operator": OPERATOR, **(filters or {})}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{BASE_URL}odpt:{resource}", params=params)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ValueError(f"ODPT returned HTTP {exc.response.status_code}.") from None
    except httpx.RequestError:
        raise ValueError("Could not reach the ODPT public API.") from None

    try:
        rows = response.json()
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError
        return rows
    except ValueError:
        raise ValueError("ODPT returned unexpected JSON-LD.") from None


def _source(dataset: str) -> Row:
    return {
        "source_url": DATASETS[dataset],
        "attribution": "東京都交通局・公共交通オープンデータ協議会",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
    }


def _page(items: list[Row], dataset: str, limit: int, offset: int = 0) -> Row:
    end = offset + limit
    return {
        "total": len(items),
        "items": items[offset:end],
        "next_offset": end if end < len(items) else None,
        **_source(dataset),
    }


def _fields(row: Row, **keys: str) -> Row:
    return {key: row.get(source_key) for key, source_key in keys.items()}


def _objects(row: Row, key: str) -> list[Row]:
    objects = row.get(key)
    if not isinstance(objects, list) or any(not isinstance(item, dict) for item in objects):
        raise ValueError("ODPT returned unexpected JSON-LD.")
    return objects


@validate_call
async def search_railway(
    kind: Literal["station", "line"], query: Query | None = None, limit: Limit = 10
) -> Row:
    """Find stations or railway lines operated by Toei, by Japanese or English name."""
    resource = "Station" if kind == "station" else "Railway"
    rows = await _fetch_rows(resource)

    try:
        items = []
        needle = query.strip().casefold() if query else ""
        name_field = f"odpt:{resource.lower()}Title"
        for row in rows:
            names = row.get(name_field) or {}
            title = names.get("ja") or row.get("dc:title")
            title_en = names.get("en")
            if not any(needle in (name or "").casefold() for name in (title, title_en)):
                continue
            item = {"id": row["owl:sameAs"], "name": title, "name_en": title_en}
            if kind == "station":
                item.update(
                    _fields(
                        row,
                        line_id="odpt:railway",
                        station_code="odpt:stationCode",
                        latitude="geo:lat",
                        longitude="geo:long",
                    )
                )
            items.append(item)
    except (KeyError, TypeError, AttributeError):
        raise ValueError("ODPT returned unexpected JSON-LD.") from None
    return {"kind": kind, "total": len(items), "items": items[:limit], **_source(kind)}


@validate_call
async def get_station_timetable(
    station_id: StationID,
    calendar_id: CalendarID | None = None,
    direction_id: DirectionID | None = None,
    limit: Limit = 10,
    offset: Offset = 0,
) -> Row:
    """Get scheduled Toei rail departures by station ID from search_railway.

    Filter by full ODPT calendar and rail direction IDs. Departures retain
    the provider's service-day order within each timetable.
    """
    rows = await _fetch_rows("StationTimetable", {"odpt:station": station_id})
    items = []
    available_timetables = []
    for row in sorted(rows, key=lambda row: str(row.get("owl:sameAs", ""))):
        timetable = _fields(
            row,
            timetable_id="owl:sameAs",
            station_id="odpt:station",
            line_id="odpt:railway",
            calendar_id="odpt:calendar",
            direction_id="odpt:railDirection",
            updated_at="dc:date",
            issued_at="dct:issued",
        )
        available_timetables.append(timetable)
        if calendar_id is not None and timetable["calendar_id"] != calendar_id:
            continue
        if direction_id is not None and timetable["direction_id"] != direction_id:
            continue
        items.extend(
            {
                **timetable,
                **_fields(
                    departure,
                    departure_time="odpt:departureTime",
                    train_type_id="odpt:trainType",
                    destination_station_ids="odpt:destinationStation",
                    is_last="odpt:isLast",
                ),
            }
            for departure in _objects(row, "odpt:stationTimetableObject")
        )
    return {
        **_page(items, "station_timetable", limit, offset),
        "available_timetables": available_timetables,
    }


@validate_call
async def get_train_status(line_id: LineID | None = None) -> Row:
    """Get Toei rail service notices with provider timestamps and expiry.

    Supply a line ID from search_railway to restrict the notices. An empty
    result means the API returned no matching notices. Check valid_until
    before using a notice as current information.
    """
    rows = await _fetch_rows("TrainInformation")
    items = [
        _fields(
            row,
            id="owl:sameAs",
            line_id="odpt:railway",
            text="odpt:trainInformationText",
            status="odpt:trainInformationStatus",
            cause="odpt:trainInformationCause",
            updated_at="dc:date",
            valid_until="dct:valid",
            originated_at="odpt:timeOfOrigin",
        )
        for row in rows
        if line_id is None or row.get("odpt:railway") == line_id
    ]
    return {"total": len(items), "items": items, **_source("train_status")}


def _fare_fields(row: Row) -> Row:
    return _fields(
        row,
        adult_ic_yen="odpt:icCardFare",
        adult_ticket_yen="odpt:ticketFare",
        child_ic_yen="odpt:childIcCardFare",
        child_ticket_yen="odpt:childTicketFare",
        updated_at="dc:date",
        issued_at="dct:issued",
    )


@validate_call
async def get_railway_fare(from_station_id: StationID, to_station_id: StationID) -> Row:
    """Get listed Toei rail fares in yen for an exact pair of station IDs."""
    rows = await _fetch_rows(
        "RailwayFare", {"odpt:fromStation": from_station_id, "odpt:toStation": to_station_id}
    )
    items = [
        {
            **_fields(row, from_station_id="odpt:fromStation", to_station_id="odpt:toStation"),
            **_fare_fields(row),
        }
        for row in rows
    ]
    return {"total": len(items), "items": items, **_source("railway_fare")}


@validate_call
async def search_bus_stops(name: Query, limit: Limit = 10, offset: Offset = 0) -> Row:
    """Find Toei bus stops by exact Japanese name and get their platform IDs."""
    rows = await _fetch_rows("BusstopPole", {"dc:title": name.strip()})
    items = [
        _fields(
            row,
            id="owl:sameAs",
            name="dc:title",
            names="title",
            platform_number="odpt:platformNumber",
            latitude="geo:lat",
            longitude="geo:long",
            route_pattern_ids="odpt:busroutePattern",
        )
        for row in sorted(rows, key=lambda row: str(row.get("owl:sameAs", "")))
    ]
    return _page(items, "bus_stop", limit, offset)


@validate_call
async def get_bus_stop_timetable(
    stop_id: BusStopID,
    calendar_id: CalendarID | None = None,
    route_id: BusRouteID | None = None,
    limit: Limit = 10,
    offset: Offset = 0,
) -> Row:
    """Get scheduled Toei bus departures from a stop ID returned by search_bus_stops.

    available_timetables lists services with their weekday/holiday labels,
    calendar IDs, and route IDs. Departures retain the provider's order.
    """
    rows = await _fetch_rows("BusstopPoleTimetable", {"odpt:busstopPole": stop_id})
    items = []
    available_timetables = []
    for row in sorted(rows, key=lambda row: str(row.get("owl:sameAs", ""))):
        timetable = _fields(
            row,
            timetable_id="owl:sameAs",
            stop_id="odpt:busstopPole",
            route_id="odpt:busroute",
            title="dc:title",
            calendar_id="odpt:calendar",
            direction_id="odpt:busDirection",
            updated_at="dc:date",
        )
        available_timetables.append(timetable)
        if calendar_id is not None and timetable["calendar_id"] != calendar_id:
            continue
        if route_id is not None and timetable["route_id"] != route_id:
            continue
        items.extend(
            {
                **timetable,
                **_fields(
                    departure,
                    departure_time="odpt:departureTime",
                    route_pattern_id="odpt:busroutePattern",
                    destination_sign="odpt:destinationSign",
                    destination_stop_id="odpt:destinationBusstopPole",
                    is_midnight="odpt:isMidnight",
                ),
            }
            for departure in _objects(row, "odpt:busstopPoleTimetableObject")
        )
    return {
        **_page(items, "bus_stop_timetable", limit, offset),
        "available_timetables": available_timetables,
    }


@validate_call
async def get_bus_route(pattern_id: BusPatternID, limit: Limit = 10, offset: Offset = 0) -> Row:
    """List stops along a Toei bus route pattern from search_bus_stops or its timetable."""
    rows = await _fetch_rows("BusroutePattern", {"owl:sameAs": pattern_id})
    items = []
    for row in rows:
        route = _fields(
            row,
            route_pattern_id="owl:sameAs",
            route_id="odpt:busroute",
            title="dc:title",
            direction="odpt:direction",
            updated_at="dc:date",
        )
        items.extend(
            {
                **route,
                **_fields(stop, stop_id="odpt:busstopPole", index="odpt:index", name="odpt:note"),
            }
            for stop in _objects(row, "odpt:busstopPoleOrder")
        )
    return _page(items, "bus_route", limit, offset)


@validate_call
async def get_bus_fare(
    pattern_id: BusPatternID, from_stop_id: BusStopID, to_stop_id: BusStopID
) -> Row:
    """Get listed Toei bus fares in yen between two stops on the same route pattern."""
    rows = await _fetch_rows(
        "BusroutePatternFare",
        {
            "odpt:fromBusroutePattern": pattern_id,
            "odpt:toBusroutePattern": pattern_id,
            "odpt:fromBusstopPole": from_stop_id,
            "odpt:toBusstopPole": to_stop_id,
        },
    )
    items = [
        {
            **_fields(
                row,
                route_pattern_id="odpt:fromBusroutePattern",
                from_stop_id="odpt:fromBusstopPole",
                to_stop_id="odpt:toBusstopPole",
                from_stop_order="odpt:fromBusstopPoleOrder",
                to_stop_order="odpt:toBusstopPoleOrder",
            ),
            **_fare_fields(row),
        }
        for row in rows
    ]
    return {"total": len(items), "items": items, **_source("bus_fare")}
