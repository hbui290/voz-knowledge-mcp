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
- `summarize_thread(url, mode="auto")`: archive the thread and create a Markdown summary.
- `search_archive(query, limit=20)`: search previously archived posts.
- `extract_links(url, mode="auto")`: archive the thread and return links/images/assets.
- `crawl_threads(urls, mode="auto", max_pages=None)`: archive several threads.

If the MCP tools are not exposed in the current environment, use the local CLI from the MCP project root:

```bash
/Users/winston/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m voz_knowledge_mcp.cli read-thread "<VOZ_URL>" --mode auto
```

## Mode Policy

Default to `mode="auto"` unless the user explicitly asks otherwise.

- `auto`: read public first as a baseline, then still try browser fallback; use the first browser endpoint that returns readable posts; if browser fallback fails, keep the public result when public worked.
- `public`: only read content visible without login.
- `browser`: skip public and read through configured Chromium-family browser endpoints.

Never ask the user for their VOZ password. Do not ask for cookies unless the user explicitly wants to reintroduce cookie-based automation; the current MCP is designed around public + browser fallback.

## Browser Fallback

When browser fallback is needed, explain that MCP uses CDP endpoints configured outside the prompt. It tries a finite ordered list and stops at the first endpoint that returns readable posts.

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

- For a newly crawled thread, state whether the result came from `public` or `browser`, how many pages/posts were archived, and where the summary/export lives if created.
- For summaries, separate signal from noise: key ideas, actionable checklist, useful links/resources, and caveats requiring verification.
- For search results, cite usernames/post IDs/timestamps when available.
- For potentially scammy or gray-market content, avoid endorsing claims; summarize neutrally and warn to verify links/files.

## Common Tasks

- User sends a VOZ thread and asks "đọc/tóm tắt/cào": call `summarize_thread(url, mode="auto")`.
- User asks "lấy link/tài nguyên trong thread": call `extract_links(url, mode="auto")`.
- User asks "tìm lại trong kho VOZ": call `search_archive(query)`.
- User sends many VOZ URLs: call `crawl_threads(urls, mode="auto")`, then summarize or search as requested.
- User asks how browser accounts are chosen: explain `VOZ_BROWSER_CDP_URLS` priority and finite fallback.
