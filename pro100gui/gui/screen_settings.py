"""Settings screen: paths, EA file, Telegram URL, EA version check."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pro100gui.adapters.ea_version_checker import (
    EAVersionChecker,
    TelegramFetchError,
)
from pro100gui.app.settings_store import AppSettings, save_settings


class SettingsScreen(QWidget):

    settingsChanged = Signal(object)  # carries AppSettings

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings

        layout = QVBoxLayout(self)

        # ----- Paths -----
        paths_box = QGroupBox("Пути")
        form = QFormLayout()

        self.mt5_install = QLineEdit(settings.mt5_install_dir)
        form.addRow("MT5 install dir:", _with_browse(self.mt5_install, self, dir_mode=True))

        self.project_dir = QLineEdit(settings.project_dir)
        form.addRow("Project (home) dir:", _with_browse(self.project_dir, self, dir_mode=True))

        self.results_dir = QLineEdit(settings.results_dir)
        form.addRow("Results dir:", _with_browse(self.results_dir, self, dir_mode=True))

        paths_box.setLayout(form)
        layout.addWidget(paths_box)

        # ----- EA -----
        ea_box = QGroupBox("EA file")
        ea_form = QFormLayout()
        self.ea_path = QLineEdit(settings.ea_path)
        ea_form.addRow("EA .ex5 path:", _with_browse(self.ea_path, self, dir_mode=False,
                                                     filter_="*.ex5"))
        self.telegram_url = QLineEdit(settings.telegram_post_url)
        ea_form.addRow("Telegram post URL:", self.telegram_url)
        ea_box.setLayout(ea_form)
        layout.addWidget(ea_box)

        # ----- Verify -----
        verify_box = QGroupBox("Проверка версии EA")
        verify_v = QVBoxLayout()
        self.verify_btn = QPushButton("Проверить EA против Telegram-поста")
        self.verify_btn.clicked.connect(self._on_verify)
        verify_v.addWidget(self.verify_btn)
        self.verify_result = QLabel("(не проверено)")
        self.verify_result.setWordWrap(True)
        verify_v.addWidget(self.verify_result)
        verify_box.setLayout(verify_v)
        layout.addWidget(verify_box)

        # ----- Save -----
        footer = QHBoxLayout()
        footer.addStretch()
        self.save_btn = QPushButton("Сохранить настройки")
        self.save_btn.clicked.connect(self._on_save)
        footer.addWidget(self.save_btn)
        layout.addLayout(footer)
        layout.addStretch()

    # ---------- actions ----------

    def _collect(self) -> AppSettings:
        return AppSettings(
            mt5_install_dir=self.mt5_install.text().strip(),
            project_dir=self.project_dir.text().strip(),
            ea_path=self.ea_path.text().strip(),
            telegram_post_url=self.telegram_url.text().strip(),
            results_dir=self.results_dir.text().strip(),
            last_session_path=self.settings.last_session_path,
        )

    def _on_save(self) -> None:
        s = self._collect()
        try:
            save_settings(s)
            self.settings = s
            self.settingsChanged.emit(s)
            self.verify_result.setText("Настройки сохранены.")
        except OSError as e:
            self.verify_result.setText(f"Не удалось сохранить: {e}")

    def _on_verify(self) -> None:
        url = self.telegram_url.text().strip() or None
        ea_path_str = self.ea_path.text().strip()
        if not ea_path_str:
            self.verify_result.setText("Сначала укажите путь к EA .ex5.")
            return
        self.verify_btn.setEnabled(False)
        self.verify_result.setText("Проверка...")
        try:
            checker = EAVersionChecker(post_url=url) if url else EAVersionChecker()
            result = checker.check(Path(ea_path_str))
            mark = "OK" if result.match else "WARNING"
            text = f"[{mark}] {result.reason}"
            if result.canonical.file_size_text:
                text += f"\nCanonical size: {result.canonical.file_size_text}"
            if result.canonical.published_at:
                text += f"\nPost time: {result.canonical.published_at}"
            self.verify_result.setText(text)
        except TelegramFetchError as e:
            self.verify_result.setText(f"Не удалось прочитать пост: {e}")
        except Exception as e:
            self.verify_result.setText(f"Ошибка: {type(e).__name__}: {e}")
        finally:
            self.verify_btn.setEnabled(True)


def _with_browse(
    line: QLineEdit, parent: QWidget, *, dir_mode: bool, filter_: str = "",
) -> QWidget:
    """Wrap a line edit in a horizontal layout with a Browse button."""
    wrap = QWidget(parent)
    h = QHBoxLayout(wrap)
    h.setContentsMargins(0, 0, 0, 0)
    h.addWidget(line)
    btn = QPushButton("...")
    btn.setMaximumWidth(40)
    h.addWidget(btn)

    def pick():
        if dir_mode:
            d = QFileDialog.getExistingDirectory(parent, "Choose folder", line.text())
            if d:
                line.setText(d)
        else:
            f, _ = QFileDialog.getOpenFileName(
                parent, "Choose file", line.text(), filter_ or "*",
            )
            if f:
                line.setText(f)

    btn.clicked.connect(pick)
    return wrap
