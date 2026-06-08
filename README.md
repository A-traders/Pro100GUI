# Pro100GUI

GUI-оркестратор для пайплайна Pro100 поверх MetaTrader 5 Strategy Tester.

Десктоп-приложение для Windows, заменяющее ручную последовательность
скриптов (`opt_pro100`, `mm_sweep`, `build_pro100_pdf`) на единое окно
с конфигурацией прогона, живым прогрессом, возобновляемостью после
сбоев и просмотром результатов.

## Установка для обычного пользователя

1. Откройте <https://github.com/A-traders/Pro100GUI/releases>.
2. Скачайте `Pro100GUI-Setup-X.Y.Z.exe` из последнего релиза.
3. Запустите. SmartScreen может предупредить -- кликните
   <b>More info</b> → <b>Run anyway</b> (установщик не подписан коммерческим сертификатом).
4. Next → Install → Finish. Программа поставится в `%LocalAppData%\Pro100GUI`,
   ярлык появится на рабочем столе и в меню Пуск. Прав администратора не требуется.

При первом запуске мастер настроек запросит путь к папке MetaTrader 5
и к файлу советника `.ex5`. После этого откроется главное окно.

**Полное руководство по работе с программой**:
[docs/UserGuide.pdf](docs/UserGuide.pdf) -- 10 страниц на русском,
описание всех вкладок, полей, кнопок, трактовка выходного PDF и
советы по использованию результатов.

## Что нужно

- Windows 10 или 11.
- MetaTrader 5 -- любая сборка (например RoboForex MT5 Terminal).
- Файл советника `.ex5` -- скачивается вручную из публичного канала
  <https://t.me/xauruspro/16>.

Python и зависимости установщик ставит сам -- ничего отдельно
устанавливать не надо.

## Сборка из исходников (для разработчика)

```
git clone https://github.com/A-traders/Pro100GUI.git
cd Pro100GUI
python -m pip install -e ".[dev]"
python -m pytest tests/
pythonw Pro100GUI.pyw
```

Сборка инсталлера:

```
python installer/build.py
```

Скрипт качает Python embeddable с python.org, ставит туда зависимости,
копирует исходники, и вызывает Inno Setup Compiler. На выходе -- один
`Pro100GUI-Setup-X.Y.Z.exe` в `installer/dist/`. Требует установленный
Inno Setup 6 (`C:\Program Files (x86)\Inno Setup 6\ISCC.exe`).

## Архитектура (5 слоев)

1. **core** -- чистая логика без GUI и MT5.
2. **adapters** -- внешние системы: `TerminalRunner`, `SetFileBuilder`,
   `IniFileBuilder`, `FilesStaging`, `EAVersionChecker`, `EARegistry`,
   `AddFrConfig`, `PdfRenderer`, `PdfQC`.
3. **orchestrator** -- DAG задач, состояние, JSON-persistence, `EventBus`.
4. **gui** -- PySide6, 4 экрана + мастер первого запуска.
5. **app** -- shell, точка входа `Pro100GUI.pyw`.

## Источник советника

Файл `.ex5` не хранится в репозитории (защита: `.gitignore`,
pre-commit hook, GitHub Actions workflow `no-ea-files`).

Пользователь скачивает `.ex5` вручную из публичного канала
<https://t.me/xauruspro/16> и указывает путь к локальному файлу в
мастере или в настройках. При запуске Pro100GUI читает Telegram-пост
и сверяет имя файла с локальным -- выводит предупреждение если
расходятся.

## Тесты

```
python -m pytest tests/
```

Должно быть 244+ passed.

## Версионирование

Версии = git-коммиты + теги. Правило `_NNN` из общего CLAUDE.md в
этом проекте не применяется.
