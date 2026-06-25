# VOZ Knowledge MCP

Local MCP server for archiving, searching, and summarizing [VOZ](https://voz.vn/) forum threads. It stores thread content locally, cleans forum noise, preserves useful links, and builds full-thread packets for AI agents to synthesize practical knowledge notes.

Target forum: [https://voz.vn/](https://voz.vn/)

## Features

- Crawl public VOZ threads and save posts/assets to SQLite.
- Use logged-in Chromium-family browser fallback when public content is incomplete.
- Search archived posts quickly, or group search results by topic.
- Build full-thread packets for long-form insight writing instead of relying on small search samples.
- Extract useful links while removing VOZ mechanics such as `goto/post?id=...`.
- Keep human-readable reports and machine-readable crawl data in local ignored folders.

## Quick Start

Requires Python 3.10+.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Run a quick public crawl:

```bash
python -m voz_knowledge_mcp.cli summarize-thread "https://voz.vn/t/example.123/" --mode public
```

Human-readable Markdown output is written under `reports/`. Crawl data, raw HTML, JSON exports, and packets are written under `archive/`.

Run as an MCP server:

```bash
python -m voz_knowledge_mcp.server
```

## MCP Client Config

Example MCP config:

```toml
[mcp_servers.voz_knowledge]
command = "/path/to/voz-knowledge-mcp/.venv/bin/python"
args = ["-m", "voz_knowledge_mcp.server"]
cwd = "/path/to/voz-knowledge-mcp"
```

Use the Python executable from your virtual environment when possible. If your MCP client launches commands through a shell, the same command is:

```bash
cd /path/to/voz-knowledge-mcp
.venv/bin/python -m voz_knowledge_mcp.server
```

Companion Codex skill for agents: `skills/voz-knowledge/SKILL.md`.

## Tools

| Tool | Use when |
| --- | --- |
| `read_thread(url, mode="auto", max_pages=None)` | Archive a VOZ thread and return structured posts/assets. |
| `summarize_thread(url, mode="auto")` | Create a readable Markdown summary under `reports/summaries/`. |
| `search_archive(query, limit=50)` | Do a quick keyword lookup in archived posts. |
| `search_archive_grouped(query, limit_per_group=5, max_matches=500)` | Search and group matching posts by topic. |
| `extract_links(url, mode="auto")` | Extract external links, images, and attachments from a thread. |
| `crawl_threads(urls, mode="auto", max_pages=None)` | Archive several threads. |
| `build_thread_packet(url, mode="auto", max_posts=None)` | Build a clean full-thread packet for insight synthesis. |
| `topic_digest(url, topic, mode="auto", max_posts=200)` | Digest one topic from the full thread. |
| `setup_browser_cdp()` | Prepare local browser fallback endpoints. |

## CLI Examples

```bash
python -m voz_knowledge_mcp.cli read-thread "https://voz.vn/t/example.123/" --mode public --max-pages 2
python -m voz_knowledge_mcp.cli summarize-thread "https://voz.vn/t/example.123/" --mode auto
python -m voz_knowledge_mcp.cli search-archive "keyword"
python -m voz_knowledge_mcp.cli search-archive-grouped "affiliate"
python -m voz_knowledge_mcp.cli build-thread-packet "https://voz.vn/t/example.123/"
python -m voz_knowledge_mcp.cli topic-digest "https://voz.vn/t/example.123/" "facebook reels"
```

## Knowledge Workflow

`search_archive` is for quick lookup only. Do not use a small search result set as the basis for full-thread insight writing.

For knowledge synthesis:

1. Archive the thread with `read_thread` or `summarize_thread`.
2. Build a full packet with `build_thread_packet`, or use `topic_digest` for one topic.
3. Remove low-signal posts such as bumps, bookmarks, thanks-only replies, app signatures, and empty replies.
4. Preserve meaningful resources: VOZ attachments, VOZ thread/post links, YouTube, Reddit, Facebook, TikTok, X/Twitter, Telegram, tool pages, files, and other external references.
5. Remove forum mechanics such as `voz.vn/goto/post?id=...`, profile/share/quote links, smilies, emoji CDN, and `data:image` placeholders.
6. Inspect preserved content links before writing a guide.
7. Treat screenshots as evidence tied to their source posts, not as standalone claims.

The companion skill includes `references/insight-writing.md` for turning long VOZ threads into useful knowledge notes.

## Read Modes

`mode="auto"` reads public content first, then tries browser mode. If a browser returns readable posts, the MCP uses the browser result and stops. If browser fallback fails, it keeps the public baseline when public worked.

`mode="public"` reads only content visible without login.

`mode="browser"` reads through configured or auto-launched Chromium-family browser endpoints.

## Browser Fallback and CDP

Browser mode uses CDP, short for Chrome DevTools Protocol. CDP is a local control port exposed by Chromium-family browsers such as Brave, Chrome, Edge, Chromium, Arc, Vivaldi, Opera, and Coc Coc.

Normal browser windows do not expose CDP. Browser mode first uses configured CDP endpoints, then automatically tries to launch installed Chromium-family browsers with local CDP ports. You can also run `setup_browser_cdp()` explicitly before crawling.

Use `127.0.0.1` endpoints only. Do not expose CDP to a public network, because anything that can reach that port can control that browser session.

Automatic launch uses dedicated local browser profiles under `archive/browser-profiles/`. Log into VOZ once in the launched profile if browser fallback needs authenticated content.

Manual override example with Brave:

```bash
/Applications/Brave\ Browser.app/Contents/MacOS/Brave\ Browser --remote-debugging-port=9222
export VOZ_BROWSER_CDP_URL=http://127.0.0.1:9222
python -m voz_knowledge_mcp.cli read-thread "https://voz.vn/t/example.123/" --mode browser
```

Multiple logged-in browsers can be tried in order:

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

Set `VOZ_AUTO_LAUNCH_BROWSERS=0` to disable automatic browser launch and use only configured CDP endpoints.

## Local Data

Paths are relative to the project directory or MCP `cwd`, not to a fixed machine path.

Human-readable documents are written under `reports/`:

- `reports/summaries/`: Markdown summaries created by `summarize_thread`.
- `reports/`: recommended place for final human-written insight notes or guides created from MCP output.

Machine-readable crawl data is written under `archive/`:

- `archive/voz_archive.sqlite`: SQLite archive.
- `archive/raw/`: raw HTML snapshots for debugging.
- `archive/exports/`: JSON exports.
- `archive/packets/`: full-thread knowledge packets.
- `archive/browser-profiles/`: dedicated browser profiles for auto-launched browser fallback.

Both `reports/` and `archive/` are ignored by git because they may contain crawled forum content, private session data, or user-specific notes.

You can override the defaults:

```bash
python -m voz_knowledge_mcp.cli --reports-dir my-reports --archive-dir my-archive summarize-thread "https://voz.vn/t/example.123/"
```

For MCP server usage, set environment variables:

```bash
VOZ_REPORTS_DIR=my-reports
VOZ_ARCHIVE_DIR=my-archive
VOZ_ARCHIVE_DB=my-archive/voz_archive.sqlite
```

## Limitations

- This project does not bypass VOZ permissions or login requirements.
- It does not store VOZ passwords.
- It does not use cookies by default.
- It does not OCR or interpret screenshots in v1.
- Search is keyword/heuristic based; semantic embedding search is not included in v1.
- MCP prepares clean source material. The final insight writing should still be done by an AI agent or human reviewer.

## Privacy and Safety

Keep this server local. Do not expose browser CDP ports publicly. Do not commit `archive/`, `reports/`, browser profiles, cookies, exported private content, or other session data.

When summarizing forum content, preserve useful source links and avoid presenting unverified claims as facts.

## Test

```bash
python -m unittest discover -s tests -v
```

## License

MIT
