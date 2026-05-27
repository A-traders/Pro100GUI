"""Tests for EAVersionChecker (golden HTML fixture + injected http stub)."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from pro100gui.adapters.ea_version_checker import (
    EAVersionChecker,
    TelegramFetchError,
    parse_post_html,
)

FIXTURE = Path(__file__).parent / "fixtures" / "tg_xauruspro_16.html"
URL = "https://t.me/xauruspro/16"


@pytest.fixture()
def fixture_html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


# ---------- parser-level tests ----------


def test_parser_extracts_filename(fixture_html: str):
    info = parse_post_html(fixture_html, URL)
    assert info.file_name == "XaurusPro100MK2_tst_008.ex5"


def test_parser_extracts_size(fixture_html: str):
    info = parse_post_html(fixture_html, URL)
    assert info.file_size_text == "219.6 KB"


def test_parser_extracts_iso_datetime(fixture_html: str):
    info = parse_post_html(fixture_html, URL)
    assert info.published_at is not None
    assert info.published_at.year == 2026
    assert info.published_at.month == 5
    assert info.published_at.day == 24
    assert info.published_at.tzinfo is not None


def test_parser_detects_edited_flag(fixture_html: str):
    info = parse_post_html(fixture_html, URL)
    assert info.edited is True


def test_parser_extracts_caption_with_html_stripped(fixture_html: str):
    info = parse_post_html(fixture_html, URL)
    assert info.caption is not None
    assert "продукта на mql5.com" in info.caption
    # The anchor tag must be gone
    assert "<a " not in info.caption
    assert "</a>" not in info.caption


def test_parser_sets_url_and_fetched_at(fixture_html: str):
    info = parse_post_html(fixture_html, URL)
    assert info.url == URL
    assert isinstance(info.fetched_at, datetime)
    assert info.fetched_at.tzinfo == timezone.utc


def test_parser_on_empty_html_returns_all_none():
    info = parse_post_html("<html></html>", URL)
    assert info.file_name is None
    assert info.file_size_text is None
    assert info.published_at is None
    assert info.edited is False
    assert info.caption is None


# ---------- EAVersionChecker tests ----------


def test_fetch_uses_embed_url():
    captured: dict = {}

    def stub(url: str) -> str:
        captured["url"] = url
        return '<div class="tgme_widget_message_document_title">x.ex5</div>'

    checker = EAVersionChecker(post_url=URL, http_get=stub)
    checker.fetch()
    assert "embed=1" in captured["url"]
    assert captured["url"].startswith(URL)


def test_fetch_embed_url_appends_with_amp_if_query_present():
    captured: dict = {}

    def stub(url: str) -> str:
        captured["url"] = url
        return '<div class="tgme_widget_message_document_title">x.ex5</div>'

    EAVersionChecker(
        post_url="https://t.me/xauruspro/16?single=1", http_get=stub,
    ).fetch()
    assert captured["url"].count("?") == 1
    assert "&embed=1" in captured["url"]


def test_fetch_returns_parsed_info(fixture_html: str):
    checker = EAVersionChecker(post_url=URL, http_get=lambda _: fixture_html)
    info = checker.fetch()
    assert info.file_name == "XaurusPro100MK2_tst_008.ex5"


def test_fetch_http_error_wraps_into_typed_exception():
    def stub(url: str) -> str:
        raise ConnectionError("offline")

    checker = EAVersionChecker(post_url=URL, http_get=stub)
    with pytest.raises(TelegramFetchError) as exc:
        checker.fetch()
    assert "offline" in str(exc.value)


def test_fetch_unparseable_response_raises():
    def stub(url: str) -> str:
        return "<html><body>Telegram error</body></html>"

    checker = EAVersionChecker(post_url=URL, http_get=stub)
    with pytest.raises(TelegramFetchError):
        checker.fetch()


def test_check_matches_when_names_equal(
    fixture_html: str, tmp_path: Path,
):
    local = tmp_path / "XaurusPro100MK2_tst_008.ex5"
    local.write_bytes(b"compiled")
    checker = EAVersionChecker(post_url=URL, http_get=lambda _: fixture_html)
    res = checker.check(local)
    assert res.match is True
    assert "matches canonical" in res.reason


def test_check_case_insensitive(fixture_html: str, tmp_path: Path):
    local = tmp_path / "XAURUSPRO100MK2_TST_008.EX5"
    local.write_bytes(b"compiled")
    res = EAVersionChecker(post_url=URL, http_get=lambda _: fixture_html).check(local)
    assert res.match is True


def test_check_mismatch_old_version(fixture_html: str, tmp_path: Path):
    local = tmp_path / "XaurusPro100MK2_tst_007.ex5"
    local.write_bytes(b"compiled")
    res = EAVersionChecker(post_url=URL, http_get=lambda _: fixture_html).check(local)
    assert res.match is False
    assert "_007" in res.reason
    assert "_008" in res.reason


def test_check_missing_local_file(fixture_html: str, tmp_path: Path):
    local = tmp_path / "never.ex5"
    res = EAVersionChecker(post_url=URL, http_get=lambda _: fixture_html).check(local)
    assert res.match is False
    assert "does not exist" in res.reason


def test_check_local_name_property(fixture_html: str, tmp_path: Path):
    local = tmp_path / "XaurusPro100MK2_tst_008.ex5"
    local.write_bytes(b"")
    res = EAVersionChecker(post_url=URL, http_get=lambda _: fixture_html).check(local)
    assert res.local_name == local.name
