from dataclasses import dataclass, field
from typing import List


@dataclass
class ParsedPost:
    post_id: str
    username: str
    timestamp: str
    body_text: str
    quotes: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)


@dataclass
class ThreadPage:
    url: str
    title: str
    page_count: int
    posts: List[ParsedPost] = field(default_factory=list)
