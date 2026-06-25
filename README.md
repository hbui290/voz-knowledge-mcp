# VOZ Knowledge MCP

Local Python MCP server for crawling public or logged-in VOZ threads, archiving posts to SQLite, and exposing search/summarization tools to an AI agent.

MCP SDK needs Python 3.10+. In this Codex workspace, use the bundled Python runtime if the system `python3` is 3.9.

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Use any Python 3.10+ runtime. Verify with:

```bash
python --version
```

## Run As MCP

```bash
python -m voz_knowledge_mcp.server
```

Companion skill for agents: `skills/voz-knowledge/SKILL.md`.

Tools exposed:

- `read_thread(url, mode="auto", max_pages=None)`
- `summarize_thread(url, mode="auto")`
- `search_archive(query, limit=20)`
- `extract_links(url, mode="auto")`
- `crawl_threads(urls, mode="auto", max_pages=None)`

## CLI

```bash
python -m voz_knowledge_mcp.cli read-thread "https://voz.vn/t/example.123/" --mode public --max-pages 2
python -m voz_knowledge_mcp.cli summarize-thread "https://voz.vn/t/example.123/" --mode public
python -m voz_knowledge_mcp.cli search-archive "youtube reup"
```

## Read Order

`mode="auto"` reads public first as a baseline, then still tries browser mode. If a browser returns readable posts, MCP uses the browser result and stops. If every browser endpoint fails, MCP keeps the public result when public worked.

`mode="public"` only reads content that anonymous visitors can see.

Browser mode connects to a Chromium-family browser you launched with remote debugging and already logged into VOZ. This works with Brave, Chrome, Edge, and similar browsers.

```bash
/Applications/Brave\ Browser.app/Contents/MacOS/Brave\ Browser --remote-debugging-port=9222
export VOZ_BROWSER_CDP_URL=http://127.0.0.1:9222
python -m voz_knowledge_mcp.cli read-thread "https://voz.vn/t/example.123/" --mode browser
```

For multiple logged-in browsers, configure them in the order you want MCP to try:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9223
/Applications/Brave\ Browser.app/Contents/MacOS/Brave\ Browser --remote-debugging-port=9222
export VOZ_BROWSER_CDP_URLS=http://127.0.0.1:9223,http://127.0.0.1:9222
python -m voz_knowledge_mcp.cli read-thread "https://voz.vn/t/example.123/" --mode browser
```

`VOZ_BROWSER_CDP_URLS` wins first. After that, the finite fallback order is:

```text
VOZ_CHROME_CDP_URL
VOZ_BRAVE_CDP_URL
VOZ_EDGE_CDP_URL
VOZ_CHROMIUM_CDP_URL
VOZ_ARC_CDP_URL
VOZ_VIVALDI_CDP_URL
VOZ_OPERA_CDP_URL
VOZ_COCCOC_CDP_URL
VOZ_BROWSER_CDP_URL
```

MCP stops at the first browser endpoint that returns readable posts. If none work, it returns an error instead of retrying forever, or keeps the public baseline when running in `auto`.

Do not put passwords in git. `archive/` is ignored.
