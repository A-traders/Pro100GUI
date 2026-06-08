"""Modal dialog asked at startup if MT5 / EA paths are not configured.

Triggered when the user has just installed the app (settings.json
empty or partial), or when they cleared the paths manually. The
dialog blocks the main window until either both paths are valid
or the user cancels -- in which case the application exits.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pro100gui.app.settings_store import AppSettings


def needs_first_run(settings: AppSettings) -> bool:
    """True iff one of the two essential paths is empty or invalid.

    Anything else (results dir, telegram URL) has a working default
    or is recoverable from the Settings tab -- only MT5 install and
    the EA .ex5 are hard prerequisites for a tester run.
    """
    if not settings.mt5_install_dir:
        return True
    if not settings.ea_path:
        return True
    install = Path(settings.mt5_install_dir)
    if not (install / "terminal64.exe").is_file():
        return True
    if not Path(settings.ea_path).is_file():
        return True
    return False


class FirstRunWizard(QDialog):
    """Single-page wizard: ask the two paths, validate, save."""

    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pro100GUI -- первый запуск")
        self.setMinimumWidth(620)
        self.setModal(True)
        # No close button -- user must confirm or cancel via buttons.
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.settings = settings

        layout = QVBoxLayout(self)

        intro = QLabel(
            "Перед первым запуском укажите два пути.\n"
            "Программа сохранит их в настройках; в дальнейшем\n"
            "это окно показываться не будет."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()

        self.mt5_dir = QLineEdit(settings.mt5_install_dir)
        form.addRow(
            "Папка установки MetaTrader 5:",
            _with_browse(self.mt5_dir, self, dir_mode=True),
        )

        self.ea_path = QLineEdit(settings.ea_path)
        form.addRow(
            "Файл советника .ex5:",
            _with_browse(self.ea_path, self, dir_mode=False, filter_="*.ex5"),
        )

        layout.addLayout(form)

        self.hint = QLabel(
            "<b>Папка MT5</b> -- та, в которой лежит файл "
            "<i>terminal64.exe</i>. У большинства брокеров это что-то "
            "вроде C:\\Program Files\\&lt;имя_брокера&gt; MT5 Terminal.<br><br>"
            "<b>Файл советника</b> -- скачивается вручную из канала "
            "<a href='https://t.me/xauruspro/16'>t.me/xauruspro/16</a> "
            "(последняя версия &mdash; XaurusPro100MK2_tst_009.ex5)."
        )
        self.hint.setOpenExternalLinks(True)
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet(
            "QLabel { background:#f5f5f5; padding:8px; "
            "border:1px solid #d0d0d0; }"
        )
        layout.addWidget(self.hint)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("QLabel { color:#c62828; }")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel,
        )
        buttons.button(QDialogButtonBox.Save).setText("Сохранить и продолжить")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена (выход)")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ---------- collection ----------

    def collected(self) -> AppSettings:
        """Return the AppSettings to persist after a successful accept."""
        # Mutate the originally-passed settings so other fields
        # (telegram URL, results dir, etc.) survive.
        self.settings.mt5_install_dir = self.mt5_dir.text().strip()
        self.settings.ea_path = self.ea_path.text().strip()
        return self.settings

    # ---------- validation ----------

    def _on_accept(self) -> None:
        mt5 = self.mt5_dir.text().strip()
        ea = self.ea_path.text().strip()
        if not mt5:
            self.error_label.setText("Укажите папку MetaTrader 5.")
            return
        if not (Path(mt5) / "terminal64.exe").is_file():
            self.error_label.setText(
                "В этой папке нет файла terminal64.exe. "
                "Выберите корневую папку MT5."
            )
            return
        if not ea:
            self.error_label.setText("Укажите файл советника .ex5.")
            return
        ea_p = Path(ea)
        if not ea_p.is_file():
            self.error_label.setText(f"Файл не найден: {ea}")
            return
        if ea_p.suffix.lower() != ".ex5":
            self.error_label.setText(
                "Это не .ex5 файл. Скачайте советник из Telegram-канала."
            )
            return
        self.error_label.setText("")
        self.accept()


def _with_browse(
    line: QLineEdit, parent: QWidget, *,
    dir_mode: bool, filter_: str = "",
) -> QWidget:
    wrap = QWidget(parent)
    h = QHBoxLayout(wrap)
    h.setContentsMargins(0, 0, 0, 0)
    h.addWidget(line)
    btn = QPushButton("...")
    btn.setMaximumWidth(40)
    h.addWidget(btn)

    def pick():
        if dir_mode:
            d = QFileDialog.getExistingDirectory(
                parent, "Выберите папку", line.text(),
            )
            if d:
                line.setText(d)
        else:
            f, _ = QFileDialog.getOpenFileName(
                parent, "Выберите файл", line.text(), filter_ or "*",
            )
            if f:
                line.setText(f)

    btn.clicked.connect(pick)
    return wrap
