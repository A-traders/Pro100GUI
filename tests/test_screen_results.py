"""Tests for ResultsScreen: enumerates PDFs in results dir."""

from __future__ import annotations

import pytest

from pro100gui.gui.screen_results import ResultsScreen


@pytest.fixture
def screen(qtbot):
    s = ResultsScreen()
    qtbot.addWidget(s)
    return s


def test_initial_state_empty(screen):
    assert screen.list.count() == 0
    assert "Results dir: -" in screen.dir_label.text()


def test_set_results_dir_lists_pdfs(qtbot, tmp_path, screen):
    (tmp_path / "Pro100_b.pdf").write_bytes(b"%PDF-1.4\n%fake\n")
    (tmp_path / "Pro100_a.pdf").write_bytes(b"%PDF-1.4\n%fake\n")
    (tmp_path / "ignored.txt").write_text("not a pdf")

    screen.set_results_dir(tmp_path)

    assert screen.list.count() == 2
    names = [screen.list.item(i).text() for i in range(screen.list.count())]
    assert names == ["Pro100_a.pdf", "Pro100_b.pdf"]
    assert str(tmp_path) in screen.dir_label.text()


def test_refresh_picks_up_new_files(tmp_path, screen):
    screen.set_results_dir(tmp_path)
    assert screen.list.count() == 0
    (tmp_path / "fresh.pdf").write_bytes(b"%PDF-1.4\n")
    screen.refresh()
    assert screen.list.count() == 1
    assert screen.list.item(0).text() == "fresh.pdf"


def test_refresh_handles_missing_dir(tmp_path, screen):
    nonexistent = tmp_path / "nope"
    screen.set_results_dir(nonexistent)
    # Should not raise, just shows nothing.
    assert screen.list.count() == 0
