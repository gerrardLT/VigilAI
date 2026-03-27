from __future__ import annotations

import html
import re
from urllib.parse import unquote

MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
URL_RE = re.compile(r"https?://\S+")
DOMAIN_FRAGMENT_RE = re.compile(r"\b(?:[\w-]+\.)+[a-z]{2,}\S*", re.IGNORECASE)
TIME_PREFIX_RE = re.compile(r"^(?:今天|昨日|昨天)\s+\d{1,2}:\d{2}\s*", re.IGNORECASE)
DATE_PREFIX_RE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}\s*")
COUNT_TITLE_RE = re.compile(r"^\d+(?:\.\d+)?[KMBW]?$", re.IGNORECASE)
PAGE_MARKER_RE = re.compile(r"\b\d+\(current\)\b", re.IGNORECASE)
LISTING_BOUNDARY_PATTERNS = [
    re.compile(r"\b今天\s+\d{1,2}:\d{2}\b", re.IGNORECASE),
    re.compile(r"\b\d+\(current\)\b", re.IGNORECASE),
    re.compile(r"\bHomepage recommendation\b", re.IGNORECASE),
    re.compile(r"\b下载APP\b", re.IGNORECASE),
    re.compile(r"\b回到顶部\b", re.IGNORECASE),
    re.compile(r"\b更多\b", re.IGNORECASE),
    re.compile(r"###\s+"),
]

NOISE_LINE_PATTERNS = [
    re.compile(r"^(?:关于我们|联系我们|原文链接|更多|下载APP|回到顶部)$", re.IGNORECASE),
    re.compile(r"^(?:today|yesterday)\s+\d{1,2}:\d{2}$", re.IGNORECASE),
    re.compile(r"^(?:今天|昨日|昨天)\s+\d{1,2}:\d{2}$", re.IGNORECASE),
    re.compile(r"^(?:follow us|share this|social media|copyright)$", re.IGNORECASE),
]

NOISE_TEXT_PATTERNS = [
    re.compile(r"!\["),
    re.compile(r"\[[^\]]+\]\(([^)]+)\)"),
    re.compile(r"%[0-9A-Fa-f]{2}"),
    re.compile(r"\b\d+\(current\)\b", re.IGNORECASE),
    re.compile(r"\bHomepage recommendation\b", re.IGNORECASE),
    re.compile(r"\b下载APP\b", re.IGNORECASE),
    re.compile(r"\b回到顶部\b", re.IGNORECASE),
]
GENERIC_NAV_TITLE_PATTERNS = [
    re.compile(r"\b(?:home|about|contact|help|faq|api|login|signup|register|terms|privacy|bookmark)\b", re.IGNORECASE),
    re.compile(r"\bHomepage recommendation\b", re.IGNORECASE),
]

LOW_SIGNAL_TITLE_PATTERNS = [
    re.compile(r"^link to project\b", re.IGNORECASE),
    re.compile(r"^cover for\b", re.IGNORECASE),
    re.compile(r"trackedtokenless protocols", re.IGNORECASE),
    re.compile(r"net revenue retained", re.IGNORECASE),
]

ASSET_URL_PATTERNS = [
    re.compile(r"\.(?:png|jpe?g|gif|webp|svg)(?:[?#\"].*)?$", re.IGNORECASE),
    re.compile(r"(?:gravatar|placeholder\.png)", re.IGNORECASE),
    re.compile(r"(?:img\.zcool\.cn|a\d+\.behance\.net|zealy-webapp-images-prod)", re.IGNORECASE),
]

SOURCE_INVALID_URL_PATTERNS = {
    "v2ex": [
        re.compile(r"v2ex\.com/(?:member|go|about|faq|mission|planes|api)", re.IGNORECASE),
        re.compile(r"gravatar", re.IGNORECASE),
    ],
    "zcool": [
        re.compile(r"img\.zcool\.cn", re.IGNORECASE),
        re.compile(r"zcool\.com\.cn/(?:designer|#!)", re.IGNORECASE),
    ],
    "behance": [
        re.compile(r"a\d+\.behance\.net", re.IGNORECASE),
    ],
    "zealy": [
        re.compile(r"(?:twitter\.com|x\.com|discord\.gg|discord\.com)", re.IGNORECASE),
        re.compile(r"zealy-webapp-images-prod", re.IGNORECASE),
    ],
    "defillama_airdrops": [
        re.compile(r"defillama\.com/(?:airdrops|earnings)$", re.IGNORECASE),
    ],
}

SOURCE_INVALID_TITLE_PATTERNS = {
    "behance": [
        re.compile(r"^link to project\b", re.IGNORECASE),
        re.compile(r"^cover for\b", re.IGNORECASE),
    ],
    "defillama_airdrops": [
        re.compile(r"trackedtokenless protocols", re.IGNORECASE),
        re.compile(r"net revenue retained", re.IGNORECASE),
    ],
}


def normalize_markdown_text(text: str, *, preserve_newlines: bool = False) -> str:
    if not text:
        return ""

    cleaned = html.unescape(unquote(text))
    cleaned = cleaned.replace("\\\\", " ")
    cleaned = MARKDOWN_IMAGE_RE.sub(" ", cleaned)
    cleaned = MARKDOWN_LINK_RE.sub(r"\1", cleaned)
    cleaned = URL_RE.sub(" ", cleaned)
    cleaned = DOMAIN_FRAGMENT_RE.sub(" ", cleaned)
    cleaned = cleaned.replace("`", " ")
    cleaned = re.sub(r"[>#*_]+", " ", cleaned)
    cleaned = cleaned.replace("|", " ")
    cleaned = cleaned.replace("·", " ")

    whitespace_pattern = r"[^\S\r\n]+" if preserve_newlines else r"\s+"
    cleaned = re.sub(whitespace_pattern, " ", cleaned)
    if preserve_newlines:
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = "\n".join(line.strip() for line in cleaned.splitlines())
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def looks_like_noisy_scraped_text(text: str | None) -> bool:
    if not text:
        return False
    return any(pattern.search(text) for pattern in NOISE_TEXT_PATTERNS)


def looks_like_invalid_activity_candidate(
    title: str | None,
    url: str | None,
    description: str | None = None,
    *,
    source_id: str | None = None,
) -> bool:
    normalized_title = normalize_markdown_text(title or "")
    normalized_description = normalize_markdown_text(description or "")
    title_lower = normalized_title.lower()
    description_lower = normalized_description.lower()
    url_lower = (url or "").lower()
    raw_title = title or ""

    if not normalized_title or len(normalized_title) < 3:
        return True
    if COUNT_TITLE_RE.fullmatch(normalized_title):
        return True
    if raw_title.lstrip().startswith("![") or raw_title.lstrip().startswith("[!") or "](" in raw_title:
        return True
    if any(pattern.search(title_lower) for pattern in GENERIC_NAV_TITLE_PATTERNS):
        return True
    if any(pattern.search(title_lower) for pattern in LOW_SIGNAL_TITLE_PATTERNS):
        return True
    if any(pattern.search(url_lower) for pattern in ASSET_URL_PATTERNS):
        return True

    source_url_patterns = SOURCE_INVALID_URL_PATTERNS.get(source_id or "", [])
    if any(pattern.search(url_lower) for pattern in source_url_patterns):
        return True

    source_title_patterns = SOURCE_INVALID_TITLE_PATTERNS.get(source_id or "", [])
    if any(pattern.search(title_lower) for pattern in source_title_patterns):
        return True

    if source_id == "zcool" and "homepage recommendation" in description_lower:
        return True
    if source_id == "behance" and ("gallery/" in url_lower and title_lower.startswith("link to project")):
        return True
    if source_id == "zealy" and any(pattern.search(url_lower) for pattern in SOURCE_INVALID_URL_PATTERNS["zealy"]):
        return True
    if source_id == "defillama_airdrops" and ("tracked" in title_lower or "bookmark" in description_lower):
        return True

    return False


def is_noise_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if COUNT_TITLE_RE.match(stripped):
        return True
    if PAGE_MARKER_RE.search(stripped):
        return True
    return any(pattern.match(stripped) for pattern in NOISE_LINE_PATTERNS)


def clean_detail_content(text: str, *, max_length: int = 10000) -> str:
    if not text:
        return ""

    cleaned_lines: list[str] = []
    for raw_line in text.splitlines():
        line = normalize_markdown_text(raw_line)
        if is_noise_line(line):
            continue
        cleaned_lines.append(line)

    cleaned = "\n\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip() + "\n\n...(内容已截断)"
    return cleaned


def build_description_from_text(text: str | None, *, title: str | None = None, max_length: int = 500) -> str:
    if not text and title:
        return title[:max_length]
    if not text:
        return ""

    cleaned = normalize_markdown_text(text)
    cleaned = _trim_listing_noise(cleaned)
    cleaned = TIME_PREFIX_RE.sub("", cleaned)
    cleaned = DATE_PREFIX_RE.sub("", cleaned)
    cleaned = re.sub(r"(?<=[。！？!?])(?:\s+[A-Za-z\u4e00-\u9fff]{1,6}){1,3}$", "", cleaned).strip()

    fragments = [fragment for fragment in _sentence_fragments(cleaned) if not _is_noise_fragment(fragment, title)]
    if fragments:
        description = " ".join(fragments[:2]).strip()
    else:
        description = cleaned

    if title and title not in description:
        description = f"{title} {description}".strip()
    if title and description.startswith(f"{title} {title}"):
        description = description[len(title) + 1 :]
        description = f"{title} {description}".strip()
    if title:
        description = _dedupe_leading_title(description, title)

    description = re.sub(r"\s{2,}", " ", description).strip()
    return description[:max_length].rstrip()


def _trim_listing_noise(text: str, *, min_offset: int = 40) -> str:
    cut_points = []
    for pattern in LISTING_BOUNDARY_PATTERNS:
        for match in pattern.finditer(text):
            if match.start() >= min_offset:
                cut_points.append(match.start())
                break
    if cut_points:
        text = text[: min(cut_points)]
    return text.strip()


def _sentence_fragments(text: str) -> list[str]:
    prepared = re.sub(r"([。！？!?])", r"\1\n", text)
    fragments = []
    for fragment in re.split(r"[\n\r]+", prepared):
        stripped = fragment.strip(" -|,;")
        if stripped:
            fragments.append(stripped)
    return fragments


def _is_noise_fragment(fragment: str, title: str | None) -> bool:
    if is_noise_line(fragment):
        return True
    if COUNT_TITLE_RE.match(fragment):
        return True
    if title and fragment == title:
        return False
    if len(fragment) <= 12 and not re.search(r"[\d。！？!?]", fragment):
        return True
    return False


def _dedupe_leading_title(description: str, title: str) -> str:
    if not description.startswith(title):
        return description

    remainder = description[len(title) :].strip()
    if not remainder:
        return title

    for fragment in _sentence_fragments(title):
        if remainder.startswith(fragment):
            remainder = remainder[len(fragment) :].strip()

    if remainder.startswith(title):
        remainder = remainder[len(title) :].strip()

    return f"{title} {remainder}".strip() if remainder else title
