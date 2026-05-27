"""Inspect the canonical EA Telegram post and compare with a local file.

The user downloads the EA binary manually from the public post
(https://t.me/xauruspro/16) and points Pro100GUI at the local path.
This adapter reads the post's embed HTML, extracts the document
filename / size / publish-or-edit time, and warns the user if the
local file's name no longer matches.

Network access is injected (constructor `http_get`) so unit tests
can pass a fixture string and golden-test the parser without
touching the internet.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_POST_URL = "https://t.me/xauruspro/16"
_EMBED_QS = "embed=1&mode=tme"

# Regex patterns -- Telegram embed class names have been stable for years.
_RE_TITLE = re.compile(
    r'class="tgme_widget_message_document_title[^"]*"[^>]*>([^<]+)<',
    re.IGNORECASE,
)
_RE_EXTRA = re.compile(
    r'class="tgme_widget_message_document_extra[^"]*"[^>]*>([^<]+)<',
    re.IGNORECASE,
)
_RE_DATETIME = re.compile(
    r'<time[^>]*datetime="([^"]+)"', re.IGNORECASE,
)
_RE_EDITED = re.compile(
    r'class="tgme_widget_message_meta"[^>]*>\s*edited\b',
    re.IGNORECASE,
)
_RE_CAPTION = re.compile(
    r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)
_RE_HTML_TAG = re.compile(r"<[^>]+>")


# ---------- public dataclasses ----------

@dataclass(frozen=True, slots=True)
class TelegramPostInfo:
    """Metadata scraped from one Telegram post's embed page."""

    url: str
    file_name: str | None
    file_size_text: str | None
    published_at: datetime | None
    edited: bool
    caption: str | None
    fetched_at: datetime


@dataclass(frozen=True, slots=True)
class VersionCheck:
    """Result of comparing a local file with the canonical post."""

    local_path: Path
    canonical: TelegramPostInfo
    match: bool
    reason: str

    @property
    def local_name(self) -> str:
        return self.local_path.name


class TelegramFetchError(RuntimeError):
    """Raised when the post page cannot be fetched or parsed at all."""


# ---------- exceptions / parsing ----------

def _strip_html(s: str) -> str:
    s = _RE_HTML_TAG.sub("", s)
    return html.unescape(s).strip()


def _parse_dt(iso: str) -> datetime | None:
    try:
        return datetime.fromisoformat(iso)
    except ValueError:
        return None


def parse_post_html(body: str, post_url: str) -> TelegramPostInfo:
    """Extract the post metadata from the embed HTML body."""
    title_m = _RE_TITLE.search(body)
    extra_m = _RE_EXTRA.search(body)
    dt_m = _RE_DATETIME.search(body)
    edited = bool(_RE_EDITED.search(body))
    cap_m = _RE_CAPTION.search(body)

    return TelegramPostInfo(
        url=post_url,
        file_name=html.unescape(title_m.group(1)).strip() if title_m else None,
        file_size_text=html.unescape(extra_m.group(1)).strip() if extra_m else None,
        published_at=_parse_dt(dt_m.group(1)) if dt_m else None,
        edited=edited,
        caption=_strip_html(cap_m.group(1)) if cap_m else None,
        fetched_at=datetime.now(timezone.utc),
    )


# ---------- HTTP ----------

def _default_http_get(url: str, timeout: float = 15.0) -> str:
    # Lazy import: requests is a runtime dep but tests inject a stub.
    import requests

    resp = requests.get(
        url, timeout=timeout,
        headers={"User-Agent": "Mozilla/5.0 Pro100GUI/0.1"},
    )
    resp.raise_for_status()
    return resp.text


# ---------- main class ----------

class EAVersionChecker:
    """Reads the canonical Telegram post and compares with a local file."""

    def __init__(
        self,
        post_url: str = DEFAULT_POST_URL,
        http_get: Callable[[str], str] | None = None,
    ) -> None:
        self.post_url = post_url
        self._http_get = http_get or _default_http_get

    def _embed_url(self) -> str:
        sep = "&" if "?" in self.post_url else "?"
        return f"{self.post_url}{sep}{_EMBED_QS}"

    def fetch(self) -> TelegramPostInfo:
        """Hit the embed URL and parse out post metadata."""
        try:
            body = self._http_get(self._embed_url())
        except Exception as e:
            raise TelegramFetchError(
                f"failed to fetch {self.post_url}: {type(e).__name__}: {e}"
            ) from e
        info = parse_post_html(body, self.post_url)
        if info.file_name is None and info.caption is None:
            raise TelegramFetchError(
                f"could not parse any post metadata from {self.post_url}; "
                f"Telegram HTML structure may have changed."
            )
        return info

    def check(self, local_path: Path) -> VersionCheck:
        """Compare the local file's name with the canonical filename.

        Match rules:
          * canonical has no filename       -> match=False (cannot verify)
          * local does not exist            -> match=False, reason cites missing
          * names equal (case-insensitive)  -> match=True
          * otherwise                       -> match=False with both names cited
        """
        info = self.fetch()
        if not local_path.exists():
            return VersionCheck(
                local_path=local_path, canonical=info, match=False,
                reason=f"local file does not exist: {local_path}",
            )
        if info.file_name is None:
            return VersionCheck(
                local_path=local_path, canonical=info, match=False,
                reason="canonical post has no document attached",
            )
        if local_path.name.lower() == info.file_name.lower():
            return VersionCheck(
                local_path=local_path, canonical=info, match=True,
                reason=f"local '{local_path.name}' matches canonical "
                       f"'{info.file_name}'",
            )
        return VersionCheck(
            local_path=local_path, canonical=info, match=False,
            reason=f"local '{local_path.name}' does NOT match canonical "
                   f"'{info.file_name}' -- download the latest version "
                   f"from {info.url}",
        )
