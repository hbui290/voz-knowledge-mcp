# VOZ Knowledge MCP

Local MCP server for archiving, searching, and summarizing [VOZ](https://voz.vn/) forum threads. It stores thread content locally, cleans forum noise, preserves useful links, and builds full-thread packets for AI agents to synthesize practical knowledge notes.

Target forum: [https://voz.vn/](https://voz.vn/)

## Features

- Crawl public VOZ threads and save posts/assets to SQLite.
- Use logged-in Chromium-family browser fallback when public content is incomplete.
- Search archived posts quickly, or group search results by topic.
- Build full-thread packets for long-form insight writing instead of relying on small search samples.
- Extract useful links while removing VOZ mechanics such as `goto/post?id=...`.
- Keep raw HTML, summaries, JSON exports, and packet outputs in a local ignored archive folder.

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
| `summarize_thread(url, mode="auto")` | Create a readable Markdown summary from a thread. |
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

Runtime data is written under `archive/`:

- `archive/voz.db`: SQLite archive.
- `archive/raw/`: raw HTML snapshots for debugging.
- `archive/summaries/`: Markdown summaries.
- `archive/exports/`: JSON exports.
- `archive/packets/`: full-thread knowledge packets.
- `archive/browser-profiles/`: dedicated browser profiles for auto-launched browser fallback.

`archive/` is ignored by git.

## Limitations

- This project does not bypass VOZ permissions or login requirements.
- It does not store VOZ passwords.
- It does not use cookies by default.
- It does not OCR or interpret screenshots in v1.
- Search is keyword/heuristic based; semantic embedding search is not included in v1.
- MCP prepares clean source material. The final insight writing should still be done by an AI agent or human reviewer.

## Privacy and Safety

Keep this server local. Do not expose browser CDP ports publicly. Do not commit `archive/`, browser profiles, cookies, exported private content, or other session data.

When summarizing forum content, preserve useful source links and avoid presenting unverified claims as facts.

## Test

```bash
python -m unittest discover -s tests -v
```

## License

MIT
