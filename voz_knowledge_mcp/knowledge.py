import json
import re
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Tuple


TOPIC_KEYWORDS = {
    "youtube": ["youtube", "ytb", "short", "shorts", "subscriber", "sub", "watch", "adsense", "bkt"],
    "ai_policy": ["ai", "voice ai", "ai voice", "ndktt", "sử dụng lại", "su dung lai", "inauthentic", "content farm"],
    "facebook_reels": ["facebook", "fb", "reel", "reels", "page", "fanpage", "rpm", "nhiệm vụ", "nhiem vu", "stars", "sao"],
    "affiliate": ["affiliate", "shopee", "amazon", "giỏ", "gio", "product card", "hoa hồng", "hoa hong", "link comment"],
    "tiktok": ["tiktok", "ttshop", "tiktok shop", "beta", "quota", "grok"],
    "copyright_music": ["public domain", "bản quyền", "ban quyen", "copyright", "nhạc", "nhac", "cover", "suno", "lofi", "audiobook", "audio book"],
    "market_ip_tax": ["ip", "vpn", "us", "eu", "mỹ", "my", "thuế", "thue", "tax", "bank", "paypal", "usd"],
    "workflow_scaling": ["tool", "workflow", "edit", "thuê", "thue", "solo", "key", "ngách", "ngach", "niche", "scale"],
}

QUESTION_HINTS = ["?", "không", "ko", "k ", "sao", "bao nhiêu", "bn ", "làm sao", "cách nào", "nên "]
SIGNAL_KEYWORDS = sorted({keyword for values in TOPIC_KEYWORDS.values() for keyword in values})
NOISE_PATTERNS = [
    r"^\s*(chấm|cham|\.{1,3}|,|phẩy|hong|hóng|book|bookmark|mark|đánh dấu|danh dau|oánh dấu|oanh dau)\s*[\.!,:;~\-_\/\\]*$",
    r"^\s*(thanks|thank|tks|thks|cảm ơn|cam on|cám ơn|dạ e cám ơn|mình cảm ơn|e cảm ơn).{0,25}$",
    r"^\s*(up|upp|7 up|ké|xin ké|theo dõi|quan tâm|lót dép|lot dep).{0,35}$",
    r"^\s*(hay|ngon|nice|ok|oke|oki|ổn quá|đỉnh quá|chúc mừng|quá bổ|bổ x).{0,35}$",
]


def parse_json_list(value) -> List[str]:
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return parsed if isinstance(parsed, list) else []


def normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()


def is_noise_post(post: Dict) -> Tuple[bool, str]:
    text = normalized_text(post.get("body_text", ""))
    links = parse_json_list(post.get("links_json", post.get("links", [])))
    images = parse_json_list(post.get("images_json", post.get("images", [])))
    if not text and not links and not images:
        return True, "empty"
    if re.search(r"(sent from my|via thenextvoz|gửi từ|gui tu)", text) and len(text) < 90:
        if not any(keyword in text for keyword in SIGNAL_KEYWORDS):
            return True, "app_signature"
    for pattern in NOISE_PATTERNS:
        if re.match(pattern, text):
            return True, "obvious_noise"
    has_signal = any(keyword in text for keyword in SIGNAL_KEYWORDS)
    is_question = any(hint in text for hint in QUESTION_HINTS)
    if len(text) < 28 and not links and not images and not (has_signal or is_question):
        return True, "low_signal_short"
    return False, ""


def is_noise_url(url: str) -> bool:
    value = (url or "").strip().lower()
    if not value:
        return True
    if value.startswith("data:image/"):
        return True
    if "voz.vn/attachments/" in value:
        return False
    if re.search(r"voz\.vn/t/[^\s]+/post-\d+", value):
        return False
    if any(domain in value for domain in ["youtube.com", "youtu.be", "reddit.com", "facebook.com", "tiktok.com", "vt.tiktok.com", "twitter.com", "x.com", "t.me", "telegram.me"]):
        return False
    noise_patterns = [
        r"voz\.vn/goto/post\?id=",
        r"voz\.vn/u/\d+/?$",
        r"voz\.vn/members/",
        r"voz\.vn/account/",
        r"voz\.vn/login/",
        r"voz\.vn/misc/",
        r"data\.voz\.vn/styles/",
        r"xenforo/smilies",
        r"/styles/(next|default)/",
        r"cdn\.jsdelivr\.net/gh/twitter/twemoji",
        r"itunes\.apple\.com/app/id1502880296",
        r"apps\.apple\.com/.*/app/.*/id1502880296",
        r"proxy\.php\?image=",
        r"/avatar",
    ]
    return any(re.search(pattern, value) for pattern in noise_patterns)


def clean_links(links: Iterable[str], images: Iterable[str]) -> Dict[str, List[Dict[str, str]]]:
    useful: List[Dict[str, str]] = []
    removed: List[Dict[str, str]] = []
    seen = set()
    for asset_type, urls in (("link", links), ("image", images)):
        for url in urls or []:
            key = (asset_type, url)
            if key in seen:
                continue
            seen.add(key)
            target = removed if is_noise_url(url) else useful
            target.append({"asset_type": asset_type, "url": url})
    return {"useful": useful, "removed": removed}


def classify_topics(post: Dict) -> List[str]:
    text = normalized_text(" ".join([post.get("body_text", ""), " ".join(parse_json_list(post.get("links_json", post.get("links", []))))]))
    topics = [topic for topic, keywords in TOPIC_KEYWORDS.items() if any(keyword in text for keyword in keywords)]
    return topics or ["general"]


def score_high_signal(post: Dict) -> int:
    text = normalized_text(post.get("body_text", ""))
    score = min(len(text) // 80, 5)
    score += len(classify_topics(post)) * 2
    if any(char.isdigit() for char in text):
        score += 2
    if parse_json_list(post.get("links_json", post.get("links", []))) or parse_json_list(post.get("images_json", post.get("images", []))):
        score += 2
    if post.get("username", "").lower() in {"hropro"}:
        score += 2
    return score


def normalize_post(post: Dict) -> Dict:
    links = parse_json_list(post.get("links_json", post.get("links", [])))
    images = parse_json_list(post.get("images_json", post.get("images", [])))
    quotes = parse_json_list(post.get("quotes_json", post.get("quotes", [])))
    cleaned = clean_links(links, images)
    base = {
        "post_id": post.get("post_id", ""),
        "username": post.get("username", ""),
        "timestamp": post.get("timestamp", ""),
        "body_text": post.get("body_text", ""),
        "quotes": quotes,
        "links": [item["url"] for item in cleaned["useful"] if item["asset_type"] == "link"],
        "images": [item["url"] for item in cleaned["useful"] if item["asset_type"] == "image"],
        "removed_links": cleaned["removed"],
    }
    base["topics"] = classify_topics(base)
    base["signal_score"] = score_high_signal(base)
    return base


def build_packet(thread: Dict, posts: List[Dict], assets: List[Dict]) -> Dict:
    clean_posts = []
    removed_posts = []
    useful_links = []
    removed_links = []
    for index, post in enumerate(posts, start=1):
        noise, reason = is_noise_post(post)
        normalized = normalize_post(post)
        normalized["thread_index"] = index
        if noise:
            normalized["noise_reason"] = reason
            removed_posts.append(normalized)
            continue
        clean_posts.append(normalized)
        for url in normalized["links"]:
            useful_links.append({"post_id": normalized["post_id"], "username": normalized["username"], "asset_type": "link", "url": url})
        for url in normalized["images"]:
            useful_links.append({"post_id": normalized["post_id"], "username": normalized["username"], "asset_type": "image", "url": url})
        for item in normalized["removed_links"]:
            removed_links.append({"post_id": normalized["post_id"], **item})

    clusters = build_topic_clusters(clean_posts)
    high_signal_posts = sorted(clean_posts, key=lambda item: (item["signal_score"], int(item["post_id"]) if str(item["post_id"]).isdigit() else 0), reverse=True)[:30]
    return {
        "thread_url": thread.get("url") or thread.get("thread_url", ""),
        "title": thread.get("title", ""),
        "source_mode": thread.get("source_mode", ""),
        "page_count": thread.get("page_count", 0),
        "total_posts": len(posts),
        "clean_posts": len(clean_posts),
        "removed_noise_posts": len(removed_posts),
        "noise_reasons": dict(Counter(post["noise_reason"] for post in removed_posts)),
        "useful_links_count": len(useful_links),
        "removed_links_count": len(removed_links),
        "topic_clusters": clusters,
        "high_signal_posts": [compact_post(post) for post in high_signal_posts],
        "useful_links": useful_links,
        "removed_noise": [compact_post(post) for post in removed_posts],
        "removed_links": removed_links,
        "posts": clean_posts,
        "assets_count": len(assets),
    }


def build_topic_clusters(posts: List[Dict], limit_per_topic: int = 8) -> Dict:
    grouped: Dict[str, List[Dict]] = defaultdict(list)
    for post in posts:
        for topic in post.get("topics", ["general"]):
            grouped[topic].append(post)
    clusters = {}
    for topic, items in grouped.items():
        representatives = sorted(items, key=lambda item: (item["signal_score"], int(item["post_id"]) if str(item["post_id"]).isdigit() else 0), reverse=True)[:limit_per_topic]
        clusters[topic] = {
            "count": len(items),
            "posts": [compact_post(post) for post in representatives],
            "links": topic_links(items, limit=10),
        }
    return dict(sorted(clusters.items()))


def topic_digest(thread: Dict, posts: List[Dict], assets: List[Dict], topic: str, max_posts: int = 200) -> Dict:
    normalized_topic = normalized_text(topic)
    topic_keywords = TOPIC_KEYWORDS.get(normalized_topic, [normalized_topic])
    clean_posts = [normalize_post(post) for post in posts if not is_noise_post(post)[0]]
    matches = [
        post
        for post in clean_posts
        if normalized_topic in post.get("topics", [])
        or any(keyword in normalized_text(post.get("body_text", "")) for keyword in topic_keywords)
        or normalized_topic in normalized_text(post.get("body_text", ""))
    ]
    matches = sorted(matches, key=lambda item: (item["signal_score"], int(item["post_id"]) if str(item["post_id"]).isdigit() else 0), reverse=True)
    limited = matches[:max_posts]
    return {
        "thread_url": thread.get("url") or thread.get("thread_url", ""),
        "title": thread.get("title", ""),
        "topic": topic,
        "matching_posts": len(matches),
        "returned_posts": len(limited),
        "posts": [compact_post(post, text_limit=700) for post in limited],
        "links": topic_links(limited, limit=30),
        "assets_count": len(assets),
    }


def compact_post(post: Dict, text_limit: int = 360) -> Dict:
    text = re.sub(r"\s+", " ", post.get("body_text", "")).strip()
    if len(text) > text_limit:
        text = text[: text_limit - 3] + "..."
    return {
        "post_id": post.get("post_id", ""),
        "username": post.get("username", ""),
        "timestamp": post.get("timestamp", ""),
        "body_text": text,
        "topics": post.get("topics", []),
        "signal_score": post.get("signal_score", 0),
        "links": post.get("links", [])[:5],
        "images": post.get("images", [])[:5],
    }


def topic_links(posts: List[Dict], limit: int) -> List[Dict[str, str]]:
    links = []
    seen = set()
    for post in posts:
        for asset_type, urls in (("link", post.get("links", [])), ("image", post.get("images", []))):
            for url in urls:
                key = (asset_type, url)
                if key in seen:
                    continue
                seen.add(key)
                links.append({"post_id": post.get("post_id", ""), "asset_type": asset_type, "url": url})
                if len(links) >= limit:
                    return links
    return links
