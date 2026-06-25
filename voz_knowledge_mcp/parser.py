import re
from typing import Iterable, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .models import ParsedPost, ThreadPage


TELEGRAM_RE = re.compile(r"\bt\(\.\)me/([A-Za-z0-9_]+)\b")


class VozParser:
    def parse_thread_page(self, html: str, url: str) -> ThreadPage:
        soup = BeautifulSoup(html, "html.parser")
        title = self._extract_title(soup)
        page_count = self._extract_page_count(soup)
        posts = [self._parse_post(article, url) for article in soup.select("article.message")]
        posts = [post for post in posts if post.body_text or post.links or post.images]
        return ThreadPage(url=url, title=title, page_count=page_count, posts=posts)

    def _extract_title(self, soup: BeautifulSoup) -> str:
        node = soup.select_one("h1.p-title-value") or soup.select_one("h1")
        if node:
            return self._clean_text(node.get_text(" ", strip=True))
        if soup.title and soup.title.string:
            return self._clean_text(soup.title.string.split("|")[0])
        return ""

    def _extract_page_count(self, soup: BeautifulSoup) -> int:
        numbers: List[int] = [1]
        for node in soup.select(".pageNav-page, .pageNavSimple-el, a[href*='page-']"):
            text = node.get_text(" ", strip=True)
            href = node.get("href") or ""
            if text.isdigit():
                numbers.append(int(text))
            match = re.search(r"page-(\d+)", href)
            if match:
                numbers.append(int(match.group(1)))
        return max(numbers)

    def _parse_post(self, article, base_url: str) -> ParsedPost:
        body = article.select_one(".bbWrapper") or article.select_one(".message-body") or article
        body_clone = BeautifulSoup(str(body), "html.parser")

        quotes = []
        for quote in body_clone.select(".bbCodeBlock, blockquote"):
            quote_text = self._clean_text(quote.get_text(" ", strip=True))
            if quote_text:
                quotes.append(quote_text)
            quote.decompose()

        body_text = self._clean_text(body_clone.get_text(" ", strip=True))
        links = self._extract_links(body, base_url, body_text)
        images = self._extract_images(body, base_url)
        links.extend(image for image in images if image not in links)

        return ParsedPost(
            post_id=self._extract_post_id(article),
            username=self._extract_username(article),
            timestamp=self._extract_timestamp(article),
            body_text=body_text,
            quotes=quotes,
            links=self._dedupe(links),
            images=self._dedupe(images),
        )

    def _extract_post_id(self, article) -> str:
        for value in (article.get("data-content"), article.get("id")):
            if not value:
                continue
            match = re.search(r"post[-_]?(\d+)|js-post-(\d+)|p(\d+)", value)
            if match:
                return next(group for group in match.groups() if group)
        return ""

    def _extract_username(self, article) -> str:
        node = article.select_one(".message-name .username") or article.select_one(".message-name")
        return self._clean_text(node.get_text(" ", strip=True)) if node else ""

    def _extract_timestamp(self, article) -> str:
        node = article.select_one("time")
        if not node:
            return ""
        return node.get("datetime") or node.get("title") or self._clean_text(node.get_text(" ", strip=True))

    def _extract_links(self, body, base_url: str, body_text: str) -> List[str]:
        links = []
        for anchor in body.select("a[href]"):
            href = anchor.get("href")
            if href:
                links.append(urljoin(base_url, href))
        for username in TELEGRAM_RE.findall(body_text):
            links.append(f"https://t.me/{username}")
        return self._dedupe(links)

    def _extract_images(self, body, base_url: str) -> List[str]:
        images = []
        for image in body.select("img"):
            src = image.get("src") or image.get("data-src") or image.get("data-url")
            if src:
                images.append(urljoin(base_url, src))
        return self._dedupe(images)

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _dedupe(self, values: Iterable[str]) -> List[str]:
        seen = set()
        result = []
        for value in values:
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result
