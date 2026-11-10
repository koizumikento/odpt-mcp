from typing import Annotated, Any, Literal

import httpx
from pydantic import Field, validate_call

BASE_URL = "https://api-public.odpt.org/api/v4/"
OPERATOR = "odpt.Operator:Toei"
DATASETS = {
    "station": "https://ckan.odpt.org/dataset/r_station-toei",
    "line": "https://ckan.odpt.org/dataset/r_route-toei",
}
Query = Annotated[str, Field(min_length=1, max_length=100, pattern=r"\S")]
Limit = Annotated[int, Field(ge=1, le=50)]


@validate_call
async def search_railway(
    kind: Literal["station", "line"], query: Query | None = None, limit: Limit = 10
) -> dict[str, Any]:
    """Find stations or railway lines operated by Toei, by Japanese or English name."""
    resource = "Station" if kind == "station" else "Railway"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{BASE_URL}odpt:{resource}", params={"odpt:operator": OPERATOR}
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ValueError(f"ODPT returned HTTP {exc.response.status_code}.") from None
    except httpx.RequestError:
        raise ValueError("Could not reach the ODPT public API.") from None

    try:
        rows = response.json()
        if not isinstance(rows, list):
            raise ValueError
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
                    {
                        "line_id": row.get("odpt:railway"),
                        "station_code": row.get("odpt:stationCode"),
                        "latitude": row.get("geo:lat"),
                        "longitude": row.get("geo:long"),
                    }
                )
            items.append(item)
    except (ValueError, KeyError, TypeError, AttributeError):
        raise ValueError("ODPT returned unexpected JSON-LD.") from None
    return {
        "kind": kind,
        "total": len(items),
        "items": items[:limit],
        "source_url": DATASETS[kind],
        "attribution": "東京都交通局・公共交通オープンデータ協議会",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
    }
