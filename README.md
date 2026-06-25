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
- `search_archive(query, limit=50)`
- `search_archive_grouped(query, limit_per_group=5, max_matches=500)`
- `extract_links(url, mode="auto")`
- `crawl_threads(urls, mode="auto", max_pages=None)`
- `build_thread_packet(url, mode="auto", max_posts=None)`
- `topic_digest(url, topic, mode="auto", max_posts=200)`
- `setup_browser_cdp()`

## Recommended Knowledge Workflow

The MCP stores raw structured forum content. `search_archive` is for quick lookup only; do not use a small search result set as the basis for full insight synthesis. For real knowledge work, use `build_thread_packet` or `topic_digest` so the agent can synthesize from full-thread source material.

A good workflow is:

1. Crawl/archive the thread with `read_thread` or `summarize_thread`.
2. Build a full packet with `build_thread_packet`.
3. Remove low-signal noise such as bumps, bookmarks, thanks-only replies, app signatures, and empty replies.
4. Clean links conservatively:
   - remove forum mechanics such as `voz.vn/goto/post?id=...`, profile/share/quote links, smilies, app signature links, emoji CDN, and `data:image` placeholders;
   - keep real resources such as VOZ attachments, VOZ thread/post links, YouTube, Reddit, Facebook, TikTok, X/Twitter, Telegram, tools, files, and external references.
5. Inspect preserved content links before writing a guide. Summarize the role of each meaningful link in the discussion.
6. Treat screenshots as evidence tied to their source posts. Link them for verification and avoid over-interpreting image-only evidence.
7. Write a natural insight guide: concrete lessons, traps, what to do, what to avoid, and why the source supports each point.

The companion skill includes `references/insight-writing.md` with the recommended style for turning long VOZ threads into useful knowledge notes.

## CLI

```bash
python -m voz_knowledge_mcp.cli read-thread "https://voz.vn/t/example.123/" --mode public --max-pages 2
python -m voz_knowledge_mcp.cli summarize-thread "https://voz.vn/t/example.123/" --mode public
python -m voz_knowledge_mcp.cli search-archive "keyword"
python -m voz_knowledge_mcp.cli search-archive-grouped "affiliate"
python -m voz_knowledge_mcp.cli build-thread-packet "https://voz.vn/t/example.123/"
python -m voz_knowledge_mcp.cli topic-digest "https://voz.vn/t/example.123/" "facebook reels"
```

## Read Order

`mode="auto"` reads public first as a baseline, then still tries browser mode. If a browser returns readable posts, MCP uses the browser result and stops. If every browser endpoint fails, MCP keeps the public result when public worked.

`mode="public"` only reads content that anonymous visitors can see.

## Browser Mode and CDP

Browser mode uses CDP, short for Chrome DevTools Protocol. CDP is a local control port exposed by Chromium-family browsers such as Brave, Chrome, Edge, Chromium, Arc, Vivaldi, Opera, and Coc Coc.

Normal browser windows do not expose CDP. Browser mode first uses configured CDP endpoints, then automatically tries to launch installed Chromium-family browsers with local CDP ports. You can also run `setup_browser_cdp()` explicitly to prepare browser fallback before crawling.

Use `127.0.0.1` endpoints only. Do not expose the CDP port to a public network, because anything that can reach that port can control that browser session.

Automatic launch uses dedicated local browser profiles under `archive/browser-profiles/`. Log into VOZ once in the launched profile if browser fallback needs authenticated content.

Manual override example with Brave:

```bash
/Applications/Brave\ Browser.app/Contents/MacOS/Brave\ Browser --remote-debugging-port=9222
export VOZ_BROWSER_CDP_URL=http://127.0.0.1:9222
python -m voz_knowledge_mcp.cli read-thread "https://voz.vn/t/example.123/" --mode browser
```

Example with multiple logged-in browsers, tried in order:

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

Set `VOZ_AUTO_LAUNCH_BROWSERS=0` to disable automatic browser launch and use only configured CDP endpoints.

Do not put passwords in git. `archive/` is ignored.
