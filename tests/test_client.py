import httpx
import pytest
import respx

from odpt_mcp import search_railway
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
