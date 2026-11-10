# odpt-mcp

都営地下鉄、東京さくらトラム、日暮里・舎人ライナーの駅・路線、時刻表、運行情報、駅間運賃を調べられます。都営バスの停留所、時刻表、経路、運賃も調べられます。データは公共交通オープンデータセンター（ODPT）から取得します。

[uv](https://docs.astral.sh/uv/) と Git が必要です。Python 3.12以上に対応しています。このツールが使う都営交通の公開APIはキー不要です。

## MCPクライアントに登録する

### Codex

```sh
codex mcp add odpt-mcp -- uvx --python 3.12 --from git+https://github.com/koizumikento/odpt-mcp.git@main odpt-mcp
codex mcp list
```

新しいセッションで `/mcp` を開いて接続を確認できます。デスクトップ版ではMCP設定画面で、下のJSON例と同じコマンド・引数を指定できます。

### Claude Desktop / Cursor

- Claude Desktop（Windows） `%APPDATA%/Claude/claude_desktop_config.json`
- Claude Desktop（macOS） `~/Library/Application Support/Claude/claude_desktop_config.json`
- Cursor `.cursor/mcp.json`（プロジェクト内）

設定ファイルの `mcpServers` に項目を追加して、クライアントを再起動してください。`uvx` が見つからない場合は実行ファイルの絶対パスを指定します。

```json
{
  "mcpServers": {
    "odpt-mcp": {
      "command": "uvx",
      "args": [
        "--python",
        "3.12",
        "--from",
        "git+https://github.com/koizumikento/odpt-mcp.git@main",
        "odpt-mcp"
      ]
    }
  }
}
```

> 都営大江戸線の新宿駅で、平日の内回りの時刻表を調べて。運行情報に案内があれば、更新時刻と一緒に教えて。

## MCPツール

| ツール | できること | 主な入力 |
| --- | --- | --- |
| `search_railway` | 都営の駅や路線を和名・英名の部分一致で検索 | `kind` は `station` または `line`、`query` は省略可 |
| `get_station_timetable` | 駅の発車時刻、方向、行先の駅ID、終電フラグを取得 | `station_id`。`calendar_id` と `direction_id` で絞り込み |
| `get_train_status` | 都営各路線の運行情報と提供元の更新時刻・有効期限を取得 | `line_id` は省略可 |
| `get_railway_fare` | 指定した駅間の大人・小児のIC運賃ときっぷ運賃を円で取得 | `from_station_id` と `to_station_id` |
| `search_bus_stops` | 都営バスの停留所を日本語名で完全一致検索し、乗り場ごとのID・座標を取得 | `name`（例「新宿駅西口」） |
| `get_bus_stop_timetable` | 停留所の発車時刻、系統、行先を取得 | `stop_id`。`calendar_id` と `route_id` で絞り込み |
| `get_bus_route` | 経路パターンに含まれる停留所を順に取得 | `pattern_id` |
| `get_bus_fare` | 同じバス経路パターン内の2停留所間の運賃を円で取得 | `pattern_id`、`from_stop_id`、`to_stop_id` |

鉄道は `search_railway` が返す `id` を後続のツールに渡します。バスは `search_bus_stops` の停留所IDから発車時刻を取得できます。経路を調べるには、停留所検索の `route_pattern_ids` または時刻表の `route_pattern_id` を使います。

- 時刻表の `available_timetables` から曜日区分と方向・系統を選べます。大江戸線の例は `odpt.Calendar:Weekday`（平日）と `odpt.RailDirection:InnerLoop`（内回り）です。バスでは各時刻表の `title` に「平日」「土曜」「休日」などの区分が含まれます。
- 時刻表は時刻表IDごとにまとまり、各時刻表内は提供元の運行日内の順序です。深夜0時台の便が23時台の後に続く場合があります。
- ページ分割するツールの `limit` は1〜50件（既定10件）です。続きは `next_offset` を `offset` に渡します。`search_railway` では `limit` のみ指定できます。
- 運行情報は照会ごとに公開APIから取得します。回答に使う際は提供元の `updated_at` と `valid_until` を確認してください。0件の場合、指定した条件に一致する案内が提供元から返っていません。運行状況と時刻表には別々のツールを使います。
- 運賃は提供元の登録額を返します。バス運賃には経路上の乗車・降車停留所IDを指定します。乗り継ぎを含む運賃計算には対応していません。
- 対応範囲は駅・停留所単位の発車時刻、鉄道の路線単位の運行案内、経路・運賃です。便単位の全停車時刻、車両位置、乗降者数、GTFS／GTFS-RTの取得は別のデータセットです。

## CLIで使う

GitHubから直接実行できます。

```sh
uvx --python 3.12 --from git+https://github.com/koizumikento/odpt-mcp.git@main odpt-mcp search-railway --kind station --query 新宿 --limit 3
```

クローン済みの場合は `uv run odpt-mcp` で同じ操作ができます。

```sh
uv run odpt-mcp get-station-timetable --station-id odpt.Station:Toei.Oedo.Shinjuku --calendar-id odpt.Calendar:Weekday --direction-id odpt.RailDirection:InnerLoop --limit 3
uv run odpt-mcp get-train-status --line-id odpt.Railway:Toei.Oedo
uv run odpt-mcp get-railway-fare --from-station-id odpt.Station:Toei.Oedo.Shinjuku --to-station-id odpt.Station:Toei.Oedo.Tochomae
uv run odpt-mcp search-bus-stops --name 新宿駅西口 --limit 3
uv run odpt-mcp get-bus-stop-timetable --stop-id odpt.BusstopPole:Toei.ShinjukuStationNishiguchi.702.1 --route-id odpt.Busroute:Toei.Shuku74 --limit 3
uv run odpt-mcp get-bus-route --pattern-id odpt.BusroutePattern:Toei.Shuku74.12001.1 --limit 3
uv run odpt-mcp get-bus-fare --pattern-id odpt.BusroutePattern:Toei.Shuku74.12001.1 --from-stop-id odpt.BusstopPole:Toei.ShinjukuStationNishiguchi.702.1 --to-stop-id odpt.BusstopPole:Toei.Kabukicho.334.2
```

結果は標準出力にUTF-8のJSONで返ります。各サブコマンドの `--help` で引数を確認できます。

## Pythonから呼び出す

```sh
git clone https://github.com/koizumikento/odpt-mcp.git
cd odpt-mcp
uv sync --locked
```

```python
import asyncio

from odpt_mcp import get_station_timetable, search_railway


async def main():
    stations = await search_railway("station", query="新宿", limit=10)
    station = next(
        item
        for item in stations["items"]
        if item["name"] == "新宿" and item["line_id"] == "odpt.Railway:Toei.Oedo"
    )
    result = await get_station_timetable(
        station["id"],
        calendar_id="odpt.Calendar:Weekday",
        direction_id="odpt.RailDirection:InnerLoop",
        limit=3,
    )
    print(result["items"])


asyncio.run(main())
```

表にある各ツールを同名の非同期関数として `odpt_mcp` からインポートできます。既にイベントループがある場合は関数を直接 `await` してください。

## 出典と利用条件

コードはMIT Licenseです。東京都交通局・公共交通オープンデータ協議会のデータを絞り込み、項目を整形して返します。各結果には出典URL、提供者名、ライセンスURLが含まれます。[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ja)

- 鉄道の出典。[駅情報](https://ckan.odpt.org/dataset/r_station-toei)・[路線情報](https://ckan.odpt.org/dataset/r_route-toei)・[駅時刻表](https://ckan.odpt.org/dataset/r_station_timetable-toei)・[運行情報](https://ckan.odpt.org/dataset/r_train_status-toei)・[運賃](https://ckan.odpt.org/dataset/r_fare-toei)
- バスの出典。[停留所](https://ckan.odpt.org/dataset/b_busstop-toei)・[停留所時刻表](https://ckan.odpt.org/dataset/b_busstop_timetable-toei)・[バス経路](https://ckan.odpt.org/dataset/b_busroute-toei)・[バス運賃](https://ckan.odpt.org/dataset/b_busfare-toei)


## 開発

```sh
uv sync --locked
uv run ruff check .
uv run ty check
uv run pytest
uv build
```
