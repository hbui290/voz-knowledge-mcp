---
name: voz-knowledge
description: Use when Codex needs to read, archive, search, extract links from, or summarize VOZ forum threads using the local voz_knowledge_mcp MCP server; triggers include VOZ URLs, requests to crawl VOZ, summarize long forum discussions, build a reusable VOZ knowledge base, search previously archived VOZ content, or use logged-in Chromium-family browser fallback without asking for passwords or cookies.
---

# VOZ Knowledge

## Overview

Use the local `voz_knowledge_mcp` server as the source of truth for VOZ thread collection. Prefer MCP tools over ad hoc browsing when the user wants reusable archive/search/summarization, not just a one-off glance.

## Tool Workflow

Use these MCP tools when available:

- `read_thread(url, mode="auto", max_pages=None)`: archive a VOZ thread and return structured posts/assets.
- `summarize_thread(url, mode="auto")`: archive the thread and create a Markdown summary under `reports/voz/summaries/`.
- `search_archive(query, limit=50)`: quick keyword lookup in archived posts; not enough for full-thread insight synthesis.
- `search_archive_grouped(query, limit_per_group=5, max_matches=500)`: keyword lookup grouped by heuristic topic.
- `extract_links(url, mode="auto")`: archive the thread and return links/images/assets.
- `crawl_threads(urls, mode="auto", max_pages=None)`: archive several threads.
- `build_thread_packet(url, mode="auto", max_posts=None)`: archive and build a clean full-thread packet for insight synthesis; writes the full packet to `archive/packets/`.
- `topic_digest(url, topic, mode="auto", max_posts=200)`: digest one topic from the full thread instead of relying on search limits.
- `setup_browser_cdp()`: launch installed Chromium-family browsers with local CDP ports for browser fallback.

If the MCP tools are not exposed in the current environment, use the local CLI from the MCP project root:

```bash
python -m voz_knowledge_mcp.cli read-thread "<VOZ_URL>" --mode auto
```

## Knowledge Workflow

When the user asks to "cao noi dung", "tong hop kien thuc", "rut insight", "viet thanh bai chia se", or anything beyond a brief summary, do not stop at `summarize_thread`. Use this workflow:

1. Archive the thread with `read_thread` or `summarize_thread` in `mode="auto"`.
2. Call `build_thread_packet` for whole-thread insight work, or `topic_digest` for one topic. Do not base insight on `search_archive` alone.
3. Remove obvious noise posts such as bumps, thanks-only replies, bookmarks, app signatures, empty replies, and jokes that add no knowledge.
4. Clean links carefully:
   - Remove forum mechanics: `voz.vn/goto/post?id=...`, quote/share links, profile links, app signature links, smilies, emoji CDN, `data:image` placeholders.
   - Preserve real resources: VOZ attachments, VOZ thread/post links, YouTube, Reddit, Facebook, TikTok, X/Twitter, Telegram, tool pages, files, and other external URLs.
5. Inspect preserved content links before writing insight:
   - Read VOZ thread/post links when accessible.
   - Open Reddit/YouTube/Facebook/TikTok/tool links when accessible; summarize their role in the discussion.
   - If a dynamic site cannot be fully inspected, say what was accessible and avoid inventing details.
6. Treat images/screenshots as evidence, not standalone content:
   - Link them beside the source post they support.
   - Summarize only what is visible or what the surrounding posts explain.
7. Write a natural insight guide, not a mechanical report. Read `references/insight-writing.md` before producing long-form knowledge artifacts.

## Mode Policy

Default to `mode="auto"` unless the user explicitly asks otherwise.

- `auto`: read public first as a baseline, then still try browser fallback; use the first browser endpoint that returns readable posts; if browser fallback fails, keep the public result when public worked.
- `public`: only read content visible without login.
- `browser`: skip public and read through configured Chromium-family browser endpoints.

Never ask the user for their VOZ password. Do not ask for cookies unless the user explicitly wants to reintroduce cookie-based automation; the current MCP is designed around public + browser fallback.

## Browser Fallback

When browser fallback is needed, do not ask the user to manually configure CDP first. The MCP tries configured CDP endpoints, then auto-launches installed Chromium-family browsers with local CDP ports. It tries a finite ordered list and stops at the first endpoint that returns readable posts.

Call `setup_browser_cdp()` proactively when a task clearly needs logged-in VOZ content or when browser fallback previously failed due to missing CDP endpoints. Automatic launch uses dedicated local profiles under `archive/browser-profiles/`; the user may need to log into VOZ once in that launched profile.

Supported environment variables, in order:

```text
VOZ_BROWSER_CDP_URLS
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

If the user has Chrome and Brave logged into different VOZ accounts, tell them to launch each browser on a different remote-debugging port and set `VOZ_BROWSER_CDP_URLS` in the desired priority order. Example:

```bash
export VOZ_BROWSER_CDP_URLS=http://127.0.0.1:9223,http://127.0.0.1:9222
```

## Response Style

For Vietnamese users, answer in Vietnamese by default. Be concise and practical:

- For a newly crawled thread, state whether the result came from `public` or `browser`, how many pages/posts were archived, and where the report/export lives if created. Human-readable VOZ Markdown reports live under `reports/voz/`; machine-readable crawl data lives under `archive/`.
- For summaries, separate signal from noise: key ideas, actionable checklist, useful links/resources, and caveats requiring verification.
- For search results, cite usernames/post IDs/timestamps when available.
- For potentially scammy or gray-market content, avoid endorsing claims; summarize neutrally and warn to verify links/files.
- For insight guides, write like a person sharing useful field notes: concrete traps, what to do, what not to do, and why the source supports it. Avoid generic filler like "lam content chat luong" unless the source gives a specific meaning.

## Common Tasks

- User sends a VOZ thread and asks "đọc/tóm tắt/cào": call `summarize_thread(url, mode="auto")`.
- User asks "lấy link/tài nguyên trong thread": call `extract_links(url, mode="auto")`.
- User asks "tìm lại trong kho VOZ": call `search_archive(query)` or `search_archive_grouped(query)` when they need patterns, not just a flat list.
- User sends many VOZ URLs: call `crawl_threads(urls, mode="auto")`, then summarize or search as requested.
- User asks how browser accounts are chosen: explain configured endpoints first, then auto-launched browser profiles, plus finite fallback.
- User asks to turn a thread into knowledge/experience/insight: call `build_thread_packet`, inspect meaningful content links, then write a natural insight guide using `references/insight-writing.md`.
