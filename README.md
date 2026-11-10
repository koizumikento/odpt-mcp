# odpt-mcp

公共交通オープンデータセンター（ODPT）で公開されている都営交通の駅と路線を探せます。都営地下鉄、東京さくらトラム、日暮里・舎人ライナーが対象です。

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

> 都営交通で「新宿」を含む駅を探して、路線IDと駅コードを教えて。

## MCPツール

### `search_railway`

`kind` は `station`（駅）または `line`（路線）です。`query` は和名・英名の部分一致で、`limit` は1〜50件です。駅を検索すると、提供元に掲載されている路線ID・駅コード・座標も返します。

## CLIで使う

```sh
uvx --python 3.12 --from git+https://github.com/koizumikento/odpt-mcp.git@main odpt-mcp search-railway --kind station --query 新宿 --limit 3
```

結果は標準出力にUTF-8のJSONで返ります。

## Pythonから呼び出す

```sh
git clone https://github.com/koizumikento/odpt-mcp.git
cd odpt-mcp
uv sync --locked
```

```python
import asyncio

from odpt_mcp import search_railway

print(asyncio.run(search_railway("station", query="新宿", limit=3)))
```

既にイベントループがある場合は関数を直接 `await` してください。

## 出典と利用条件

コードはMIT Licenseです。データ提供元は東京都交通局・公共交通オープンデータ協議会です。元データを絞り込み、項目を整形して返します。[駅情報](https://ckan.odpt.org/dataset/r_station-toei)・[路線情報](https://ckan.odpt.org/dataset/r_route-toei)・[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ja)

## 開発

```sh
uv sync --locked
uv run ruff check .
uv run ty check
uv run pytest
uv build
```
