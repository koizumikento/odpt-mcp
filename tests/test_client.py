import httpx
import pytest
import respx

from odpt_mcp import (
    get_bus_fare,
    get_bus_route,
    get_bus_stop_timetable,
    get_railway_fare,
    get_station_timetable,
    get_train_status,
    search_bus_stops,
    search_railway,
)
from odpt_mcp.client import BASE_URL


@pytest.mark.asyncio
@respx.mock
async def test_toei_station_search_matches_english_title() -> None:
    route = respx.get(BASE_URL + "odpt:Station").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "owl:sameAs": "odpt.Station:Toei.Oedo.Shinjuku",
                    "dc:title": "新宿",
                    "odpt:stationTitle": {"en": "Shinjuku"},
                    "odpt:railway": "odpt.Railway:Toei.Oedo",
                },
                {"owl:sameAs": "odpt.Station:Toei.Mita.Hakusan", "dc:title": "白山"},
            ],
        )
    )
    result = await search_railway("station", "SHINJUKU")
    assert dict(route.calls[0].request.url.params) == {"odpt:operator": "odpt.Operator:Toei"}
    assert result["total"] == 1
    assert result["items"][0]["line_id"] == "odpt.Railway:Toei.Oedo"


@pytest.mark.asyncio
@respx.mock
async def test_station_timetable_filters_and_preserves_service_day_order() -> None:
    station_id = "odpt.Station:Toei.Oedo.Shinjuku"
    calendar_id = "odpt.Calendar:Weekday"
    direction_id = "odpt.RailDirection:InnerLoop"
    weekday = {
        "owl:sameAs": "odpt.StationTimetable:Toei.Oedo.Shinjuku.InnerLoop.Weekday",
        "odpt:station": station_id,
        "odpt:railDirection": direction_id,
        "odpt:calendar": calendar_id,
        "odpt:stationTimetableObject": [
            {"odpt:departureTime": "23:48"},
            {"odpt:departureTime": "00:12", "odpt:isLast": True},
        ],
    }
    route = respx.get(BASE_URL + "odpt:StationTimetable").respond(
        json=[
            {**weekday, "odpt:calendar": "odpt.Calendar:SaturdayHoliday"},
            {**weekday, "odpt:railDirection": "odpt.RailDirection:OuterLoop"},
            weekday,
        ]
    )

    first = await get_station_timetable(station_id, calendar_id, direction_id, limit=1)
    last = await get_station_timetable(station_id, calendar_id, direction_id, limit=1, offset=1)

    assert route.calls[0].request.url.params["odpt:station"] == station_id
    assert first["total"] == 2
    assert first["items"][0]["departure_time"] == "23:48"
    assert len(first["available_timetables"]) == 3
    assert first["next_offset"] == 1
    assert last["items"][0]["departure_time"] == "00:12"
    assert last["items"][0]["is_last"] is True
    assert last["next_offset"] is None


@pytest.mark.asyncio
@respx.mock
async def test_train_status_keeps_source_time_and_filters_line() -> None:
    line_id = "odpt.Railway:Toei.Oedo"
    respx.get(BASE_URL + "odpt:TrainInformation").respond(
        json=[
            {"odpt:railway": "odpt.Railway:Toei.Mita"},
            {
                "odpt:railway": line_id,
                "odpt:trainInformationText": {"ja": "運転見合わせ"},
                "dc:date": "2026-11-10T10:00:00+09:00",
                "dct:valid": "2026-11-10T10:05:00+09:00",
                "odpt:timeOfOrigin": "2026-11-10T09:59:00+09:00",
            },
        ]
    )

    result = await get_train_status(line_id)
    assert result["total"] == 1
    item = result["items"][0]
    assert item["text"]["ja"] == "運転見合わせ"
    assert item["updated_at"] == "2026-11-10T10:00:00+09:00"
    assert item["valid_until"] == "2026-11-10T10:05:00+09:00"
    assert item["originated_at"] == "2026-11-10T09:59:00+09:00"
    assert (await get_train_status("odpt.Railway:Toei.Asakusa"))["total"] == 0


@pytest.mark.asyncio
@respx.mock
async def test_railway_fare_preserves_fare_categories() -> None:
    station_id = "odpt.Station:Toei.Oedo.Shinjuku"
    destination_id = "odpt.Station:Toei.Oedo.Tochomae"
    route = respx.get(BASE_URL + "odpt:RailwayFare").respond(
        json=[
            {
                "odpt:fromStation": station_id,
                "odpt:toStation": destination_id,
                "odpt:icCardFare": 178,
                "odpt:ticketFare": 180,
                "odpt:childIcCardFare": 89,
                "odpt:childTicketFare": 90,
            }
        ]
    )

    result = await get_railway_fare(station_id, destination_id)
    assert route.calls[0].request.url.params["odpt:fromStation"] == station_id
    assert route.calls[0].request.url.params["odpt:toStation"] == destination_id
    item = result["items"][0]
    assert [item[key] for key in ("adult_ic_yen", "adult_ticket_yen")] == [178, 180]
    assert [item[key] for key in ("child_ic_yen", "child_ticket_yen")] == [89, 90]


@pytest.mark.asyncio
@respx.mock
async def test_bus_stop_timetable_links_to_route_pattern() -> None:
    stop_id = "odpt.BusstopPole:Toei.ShinjukuStationNishiguchi.702.1"
    pattern_id = "odpt.BusroutePattern:Toei.Shuku74.12001.1"
    stop_route = respx.get(BASE_URL + "odpt:BusstopPole").respond(
        json=[
            {
                "owl:sameAs": stop_id,
                "dc:title": "新宿駅西口",
                "odpt:busroutePattern": [pattern_id],
            }
        ]
    )
    timetable_route = respx.get(BASE_URL + "odpt:BusstopPoleTimetable").respond(
        json=[
            {
                "odpt:busstopPole": stop_id,
                "odpt:calendar": "odpt.Calendar:Specific.Toei.13-170",
                "odpt:busstopPoleTimetableObject": [
                    {"odpt:departureTime": "08:05", "odpt:busroutePattern": pattern_id}
                ],
            }
        ]
    )
    pattern_route = respx.get(BASE_URL + "odpt:BusroutePattern").respond(
        json=[
            {
                "owl:sameAs": pattern_id,
                "odpt:busstopPoleOrder": [
                    {"odpt:index": 1, "odpt:busstopPole": stop_id, "odpt:note": "新宿駅西口"}
                ],
            }
        ]
    )

    stops = await search_bus_stops("新宿駅西口")
    departures = await get_bus_stop_timetable(stops["items"][0]["id"])
    result = await get_bus_route(departures["items"][0]["route_pattern_id"])

    assert stop_route.calls[0].request.url.params["dc:title"] == "新宿駅西口"
    assert timetable_route.calls[0].request.url.params["odpt:busstopPole"] == stop_id
    assert pattern_route.calls[0].request.url.params["owl:sameAs"] == pattern_id
    assert result["items"][0]["stop_id"] == stop_id
    assert result["items"][0]["index"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_bus_fare_matches_two_platforms_on_the_route_pattern() -> None:
    pattern_id = "odpt.BusroutePattern:Toei.Shuku74.12001.1"
    from_id = "odpt.BusstopPole:Toei.ShinjukuStationNishiguchi.702.1"
    to_id = "odpt.BusstopPole:Toei.Kabukicho.334.2"
    filters = {
        "odpt:fromBusroutePattern": pattern_id,
        "odpt:toBusroutePattern": pattern_id,
        "odpt:fromBusstopPole": from_id,
        "odpt:toBusstopPole": to_id,
    }
    route = respx.get(BASE_URL + "odpt:BusroutePatternFare").respond(
        json=[
            {
                **filters,
                "odpt:fromBusstopPoleOrder": 1,
                "odpt:toBusstopPoleOrder": 2,
                "odpt:icCardFare": 210,
                "odpt:childTicketFare": 110,
            }
        ]
    )

    result = await get_bus_fare(pattern_id, from_id, to_id)

    assert dict(route.calls[0].request.url.params) == {
        "odpt:operator": "odpt.Operator:Toei",
        **filters,
    }
    item = result["items"][0]
    assert item["from_stop_order"] == 1
    assert item["to_stop_order"] == 2
    assert item["adult_ic_yen"] == 210
    assert item["child_ticket_yen"] == 110
