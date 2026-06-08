"""Сборка docs/UserGuide.pdf -- руководство пользователя Pro100GUI.

10 страниц на русском: 1 -- установка, остальные -- интерфейс,
поля, кнопки, трактовка выходного PDF, использование результатов.

Запуск:
    python docs/build_user_guide.py
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ---------- fonts ----------

FONTS_DIR = Path(r"C:\Windows\Fonts")
pdfmetrics.registerFont(TTFont("Body", str(FONTS_DIR / "arial.ttf")))
pdfmetrics.registerFont(TTFont("Bold", str(FONTS_DIR / "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("Italic", str(FONTS_DIR / "ariali.ttf")))
pdfmetrics.registerFont(TTFont("Mono", str(FONTS_DIR / "consola.ttf")))
registerFontFamily(
    "Body", normal="Body", bold="Bold", italic="Italic", boldItalic="Bold",
)

# ---------- styles ----------

BASE = getSampleStyleSheet()
H1 = ParagraphStyle(
    "H1", parent=BASE["Title"], fontName="Bold", fontSize=22,
    textColor=colors.HexColor("#1a237e"), spaceAfter=14, leading=26,
    alignment=TA_LEFT,
)
H2 = ParagraphStyle(
    "H2", parent=BASE["Heading2"], fontName="Bold", fontSize=15,
    textColor=colors.HexColor("#1a237e"), spaceBefore=14, spaceAfter=8,
    leading=19,
)
H3 = ParagraphStyle(
    "H3", parent=BASE["Heading3"], fontName="Bold", fontSize=11.5,
    textColor=colors.HexColor("#283593"), spaceBefore=8, spaceAfter=3,
    leading=14,
)
BODY = ParagraphStyle(
    "BODY", parent=BASE["BodyText"], fontName="Body", fontSize=10,
    leading=13.5, spaceAfter=5, alignment=TA_LEFT,
)
CODE = ParagraphStyle(
    "CODE", parent=BASE["Code"], fontName="Mono", fontSize=9,
    leading=12, leftIndent=10, spaceBefore=3, spaceAfter=6,
    backColor=colors.HexColor("#f4f4f4"), borderPadding=5,
    borderColor=colors.HexColor("#d0d0d0"), borderWidth=0.5,
)
NOTE = ParagraphStyle(
    "NOTE", parent=BODY, leftIndent=8, rightIndent=8,
    backColor=colors.HexColor("#fff8e1"),
    borderColor=colors.HexColor("#ffb300"), borderWidth=0.5,
    borderPadding=6, spaceBefore=4, spaceAfter=8,
    textColor=colors.HexColor("#5d4037"),
)
WARN = ParagraphStyle(
    "WARN", parent=NOTE,
    backColor=colors.HexColor("#ffebee"),
    borderColor=colors.HexColor("#c62828"),
    textColor=colors.HexColor("#b71c1c"),
)
TIP = ParagraphStyle(
    "TIP", parent=NOTE,
    backColor=colors.HexColor("#e8f5e9"),
    borderColor=colors.HexColor("#2e7d32"),
    textColor=colors.HexColor("#1b5e20"),
)

# ---------- helpers ----------

def p(t, s=BODY): return Paragraph(t, s)
def code(t):
    s = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = s.replace("\n", "<br/>")
    return Paragraph(s, CODE)
def note(t): return Paragraph("<b>Подсказка.</b> " + t, NOTE)
def warn(t): return Paragraph("<b>Внимание.</b> " + t, WARN)
def tip(t): return Paragraph("<b>Совет.</b> " + t, TIP)

CELL = ParagraphStyle(
    "CELL", parent=BODY, fontName="Body", fontSize=9.5,
    leading=12, spaceAfter=0,
)
CELL_BOLD = ParagraphStyle(
    "CELL_BOLD", parent=CELL, fontName="Bold",
)


def kv_table(rows, col_widths=(45 * mm, 110 * mm)):
    """Build a table with auto-wrapping cells.

    First row -> header (bold, shaded). Plain strings are wrapped
    in Paragraph so long text wraps inside the column instead of
    overflowing past the right edge.
    """
    wrapped = []
    for r, row in enumerate(rows):
        new_row = []
        for cell in row:
            if isinstance(cell, str):
                style = CELL_BOLD if r == 0 else CELL
                new_row.append(Paragraph(cell, style))
            else:
                new_row.append(cell)
        wrapped.append(new_row)
    t = Table(wrapped, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eaf6")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdbdbd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    return t

def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Body", 8)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawRightString(
        A4[0] - 15 * mm, 12 * mm,
        f"Pro100GUI -- руководство пользователя  |  стр. {doc.page}",
    )
    canvas.restoreState()

# ============================================================
# CONTENT
# ============================================================

def build_story():
    s = []

    # ====== Page 1: Title ======
    s.append(Spacer(1, 22 * mm))
    s.append(p("Pro100GUI", H1))
    s.append(p(
        "Руководство пользователя",
        ParagraphStyle("subtitle", parent=BODY, fontSize=13, leading=17,
                      textColor=colors.HexColor("#283593"), spaceAfter=14),
    ))
    s.append(p(
        "Pro100GUI -- это десктоп-приложение для Windows, которое "
        "автоматизирует прогон стратегического тестера MetaTrader 5 для "
        "пайплайна Pro100. Программа последовательно выполняет фазы "
        "оптимизации (BACK), форвард-теста (FORWARD) и при желании "
        "прогон по реальным тикам (REAL) для нескольких таймфреймов, "
        "а по итогу собирает интерактивный PDF-отчет с лучшими сетапами."
    ))
    s.append(p(
        "Документ рассчитан на пользователя, который владеет Windows на "
        "уровне обычного пользователя -- скачать, установить, запустить из "
        "меню Пуск. Знание Python, командной строки и git не требуется."
    ))
    s.append(Spacer(1, 6 * mm))
    s.append(p("Содержание", H3))
    toc = [
        ("1. Установка", 2),
        ("2. Первый запуск -- мастер настроек", 3),
        ("3. Главное окно: четыре вкладки", 4),
        ("4. Вкладка Конфигурация", 5),
        ("5. Вкладка Прогон", 6),
        ("6. Вкладки Результаты и Настройки", 7),
        ("7. Что внутри выходного PDF", 8),
        ("8. Как использовать результаты дальше", 9),
        ("9. Возобновление и решение проблем", 10),
    ]
    toc_data = [[name, str(page)] for name, page in toc]
    toc_t = Table(toc_data, colWidths=[130 * mm, 20 * mm])
    toc_t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Body", 10.5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    s.append(toc_t)

    # ====== Page 2: Установка ======
    s.append(PageBreak())
    s.append(p("1. Установка", H2))
    s.append(p(
        "Pro100GUI распространяется одним файлом-установщиком. Python и "
        "все зависимости упакованы внутрь -- ничего отдельно ставить не надо."
    ))
    s.append(p("Шаг 1. Скачать установщик", H3))
    s.append(p(
        "Откройте страницу: <b>https://github.com/A-traders/Pro100GUI/releases</b>"
    ))
    s.append(p(
        "В разделе <b>Latest release</b> найдите файл "
        "<i>Pro100GUI-Setup-X.Y.Z.exe</i> и скачайте его (~150 МБ)."
    ))
    s.append(p("Шаг 2. Запустить", H3))
    s.append(p(
        "Двойной клик по скачанному файлу. Windows SmartScreen может показать "
        "синее окно <i>Windows protected your PC</i> -- кликните "
        "<b>More info</b>, затем <b>Run anyway</b>. Это разовая операция "
        "(возникает потому, что установщик не подписан коммерческим сертификатом)."
    ))
    s.append(p("Шаг 3. Пройти мастер", H3))
    s.append(p(
        "Установщик предложит выбрать язык (русский / English), "
        "примите лицензию и нажимайте <b>Next</b>. По умолчанию программа "
        "ставится в <i>%LocalAppData%\\Pro100GUI</i> -- это папка вашего "
        "пользователя, прав администратора не требует."
    ))
    s.append(p(
        "На последнем экране включена галка <b>Создать ярлык на рабочем столе</b>. "
        "Жмите <b>Install</b>, дождитесь окончания (~30 секунд), затем "
        "<b>Finish</b>. Программа запустится автоматически."
    ))
    s.append(p("Что появилось после установки", H3))
    s.append(kv_table([
        ["Где", "Что"],
        ["Рабочий стол", "Ярлык Pro100GUI"],
        ["Меню Пуск", "Папка Pro100GUI -> Pro100GUI / User Guide / Uninstall"],
        ["Программы и компоненты", "Запись Pro100GUI (для удаления)"],
        ["Папка установки", "%LocalAppData%\\Pro100GUI"],
        ["Папка настроек", "%AppData%\\Pro100GUI (создается при первом запуске)"],
    ]))
    s.append(tip(
        "Папка с настройками <i>%AppData%\\Pro100GUI</i> переживает удаление "
        "и переустановку программы -- ваши пути к MT5 и результаты не "
        "пропадут при обновлении."
    ))

    # ====== Page 3: First-run wizard ======
    s.append(PageBreak())
    s.append(p("2. Первый запуск -- мастер настроек", H2))
    s.append(p(
        "При самом первом запуске (или если папка с настройками была "
        "удалена) откроется небольшой диалог <b>Pro100GUI -- первый запуск</b>. "
        "Он запрашивает два пути, без которых программа работать не сможет."
    ))
    s.append(p("Папка установки MetaTrader 5", H3))
    s.append(p(
        "Корневая папка вашего MT5, в которой лежит файл <i>terminal64.exe</i>. "
        "У большинства брокеров это что-то вроде:"
    ))
    s.append(code(r"C:\Program Files\RoboForex MT5 Terminal"))
    s.append(p(
        "Кликните кнопку <b>...</b> справа от поля, выберите папку через "
        "диалог. Программа проверит, что в ней действительно есть "
        "<i>terminal64.exe</i>."
    ))
    s.append(warn(
        "Это должен быть отдельный экземпляр MT5, который вы готовы "
        "отдать под тесты. Pro100GUI запускает его в режиме portable и "
        "может занимать его на несколько часов. Не указывайте сюда "
        "терминал, через который ведете живую торговлю."
    ))
    s.append(p("Файл советника .ex5", H3))
    s.append(p(
        "Скачивается вручную из публичного канала "
        "<b>https://t.me/xauruspro/16</b>. В посте прикреплен файл с "
        "именем вида <i>XaurusPro100MK2_tst_009.ex5</i> (актуальная версия "
        "может отличаться). Скачайте его в любую удобную папку, например "
        "в Документы. Затем в мастере кликните <b>...</b>, выберите этот "
        "файл."
    ))
    s.append(p("Кнопки внизу", H3))
    s.append(kv_table([
        ["Кнопка", "Действие"],
        ["Сохранить и продолжить",
         "Проверяет оба пути и открывает главное окно"],
        ["Отмена (выход)",
         "Закрывает программу. Без путей она работать не может"],
    ]))
    s.append(p(
        "Если что-то указано неверно (нет terminal64.exe в папке, "
        "файл не найден, не .ex5) -- мастер покажет ошибку красным "
        "и не закроется."
    ))

    # ====== Page 4: Main window overview ======
    s.append(PageBreak())
    s.append(p("3. Главное окно: четыре вкладки", H2))
    s.append(p(
        "После мастера откроется главное окно. Сверху -- четыре вкладки, "
        "переключаются обычным кликом."
    ))
    s.append(kv_table(
        [
            ["Вкладка", "Назначение"],
            ["Конфигурация",
             "Здесь вы задаете параметры прогона: даты, символ, депозит, "
             "набор таймфреймов. С этой вкладки запускается прогон кнопкой Start."],
            ["Прогон",
             "Открывается автоматически после Start. Живой список фаз с "
             "цветными статусами, лог-окно, кнопка Cancel. Сюда вы смотрите "
             "пока идет тестирование."],
            ["Результаты",
             "Список готовых PDF-отчетов из всех ваших прогонов. Двойной "
             "клик открывает PDF в системном просмотрщике. Также есть кнопка "
             "Открыть папку результатов."],
            ["Настройки",
             "Все те же пути что в мастере (можно поменять), плюс настройка "
             "папки результатов, ссылка на Telegram-пост, кнопка проверки "
             "актуальности версии советника."],
        ],
        col_widths=(35 * mm, 120 * mm),
    ))
    s.append(p("Что происходит при запуске", H3))
    s.append(p(
        "1. Мастер первого запуска (только если не настроены MT5 / EA -- см. п. 2)."
    ))
    s.append(p(
        "2. Проверка незавершенной сессии: если в прошлый раз вы прервали "
        "прогон, появится диалог <b>Продолжить / Новая сессия / Отмена</b>."
    ))
    s.append(p(
        "3. Открывается главное окно на вкладке Конфигурация."
    ))
    s.append(tip(
        "Все ваши настройки автоматически сохраняются в "
        "<i>%AppData%\\Pro100GUI\\settings.json</i>. В обычной работе "
        "редактировать его вручную не нужно."
    ))

    # ====== Page 5: Конфигурация ======
    s.append(PageBreak())
    s.append(p("4. Вкладка Конфигурация", H2))
    s.append(p(
        "На этой вкладке вы описываете один прогон. Все поля имеют разумные "
        "умолчания -- если не уверены, оставляйте как есть."
    ))
    s.append(p("Параметры прогона", H3))
    s.append(kv_table([
        ["Поле", "Что задает"],
        ["End date",
         "Последний день, до которого считается FORWARD. Программа сама "
         "посчитает все back и forward окна назад от этой даты."],
        ["Symbol",
         "Торговый символ. По умолчанию XAUUSD. Должен присутствовать в "
         "обзоре рынка вашего MT5 (Market Watch)."],
        ["Min depo",
         "Депозит счета в тестере MT5. По умолчанию 10 000. Сетапы, на "
         "которых стратегия сливает с этим депозитом, отсеиваются."],
        ["Snap dates to 1st of month",
         "Округлять расчетные окна к 1-му числу месяца. Включено по "
         "умолчанию -- стандартная практика для воспроизводимости."],
        ["Run REAL phase",
         "Если включено -- после FORWARD будет еще один прогон топ-сетапов "
         "по реальным тикам. Добавляет ~1-2 часа на прогон."],
    ]))
    s.append(p("Таблица Timeframe plans", H3))
    s.append(p(
        "Список таймфреймов, на которых тестируем. Каждая строка -- один TF "
        "и его пара чисел Back / Forward в месяцах. Forward почти всегда "
        "вдвое длиннее Back -- так зашиты умолчания."
    ))
    s.append(p(
        "Кнопка <b>Add TF</b> добавляет новую строку с дефолтом M5 (4/8). "
        "<b>Remove selected</b> удаляет выделенную строку. Менять TF в "
        "выпадающем списке, числа -- стрелочками или прямым вводом."
    ))
    s.append(kv_table(
        [
            ["TF", "Back", "Forward", "Длительность фазы"],
            ["M1",  "3",   "6",       "~50-90 минут"],
            ["M5",  "4",   "8",       "~30-60 минут"],
            ["M15", "5",   "10",      "~20-40 минут"],
            ["M30", "6",   "12",      "~15-30 минут"],
            ["H1",  "8",   "16",      "~10-20 минут"],
        ],
        col_widths=(15 * mm, 22 * mm, 28 * mm, 75 * mm),
    ))
    s.append(p("Кнопка Start", H3))
    s.append(p(
        "Внизу справа. Запускает прогон, программа автоматически "
        "переключается на вкладку <b>Прогон</b>. Если что-то не задано "
        "(например пустая таблица TF) -- в статус-строке появится подсказка, "
        "и Start не сработает."
    ))

    # ====== Page 6: Прогон ======
    s.append(PageBreak())
    s.append(p("5. Вкладка Прогон", H2))
    s.append(p(
        "Здесь вы наблюдаете за работой программы. Не закрывайте окно "
        "пока идет прогон -- но можете спокойно работать в других "
        "программах, Pro100GUI занимает минимум CPU."
    ))
    s.append(p("Шапка", H3))
    s.append(p(
        "<b>Session: 20260608_143205_abcdef (5 phases)</b> -- идентификатор "
        "сессии (по нему ищется PDF в Результатах) и общее число фаз. "
        "Справа кнопка <b>Cancel</b>."
    ))
    s.append(p("Дерево фаз", H3))
    s.append(p("Каждая строка -- один job. Колонки:"))
    s.append(kv_table([
        ["Колонка", "Что показывает"],
        ["Job", "Имя фазы (например M5.BACK или M5.FORWARD), PDF -- финальная"],
        ["Status",
         "Текущий статус цветом: серое PENDING (ждет), синее RUNNING (идет), "
         "зеленое DONE (готово), красное FAILED (упало), серое SKIPPED "
         "(пропущено после ошибки)"],
        ["Duration", "Сколько секунд заняла фаза (после завершения)"],
        ["Rows",
         "Сколько строк в результирующем pro100.csv после фазы. Для PDF -- "
         "общее число строк во всем отчете"],
        ["Notes",
         "Сообщение об ошибке если FAILED, или причина SKIPPED"],
    ]))
    s.append(p("Лог", H3))
    s.append(p(
        "Прокручивается автоматически. Содержит технические сообщения от "
        "программы и от MetaTrader. Полезен если фаза упала -- увидите там "
        "конкретную ошибку. В обычной успешной работе лог можно не читать."
    ))
    s.append(p("Кнопка Cancel", H3))
    s.append(p(
        "Останавливает прогон ПОСЛЕ завершения текущей фазы. Мгновенно "
        "прерывать тестер на полпути нельзя -- он может оставить мусор. "
        "Уже выполненные фазы помечаются DONE, текущая дорабатывает, "
        "остальные становятся SKIPPED. Сессия сохраняется -- ее можно "
        "продолжить позже (см. п. 9)."
    ))
    s.append(warn(
        "Пока идет прогон, не запускайте MetaTrader 5 в той же папке, "
        "что указана в Настройках Pro100GUI -- они не смогут работать "
        "одновременно. Программа сама проверяет это перед каждой фазой и "
        "откажется стартовать если терминал уже запущен."
    ))

    # ====== Page 7: Результаты + Настройки ======
    s.append(PageBreak())
    s.append(p("6. Вкладки Результаты и Настройки", H2))
    s.append(p("Результаты", H3))
    s.append(p(
        "Список PDF-файлов в текущей папке результатов. По умолчанию это "
        "<i>%AppData%\\Pro100GUI\\results\\</i>, можно сменить в Настройках. "
        "Имя файла -- <i>Pro100_&lt;session_id&gt;.pdf</i>."
    ))
    s.append(kv_table([
        ["Кнопка", "Действие"],
        ["Refresh",
         "Перечитать список (если вы вручную положили файл в папку)"],
        ["Open selected",
         "Открыть выбранный PDF в системном просмотрщике "
         "(Edge / Adobe Reader / что у вас по умолчанию)"],
        ["Open results folder",
         "Открыть саму папку с результатами в Проводнике"],
    ]))
    s.append(p(
        "Помимо PDF в этой же папке лежат отдельные CSV для каждой фазы "
        "(<i>pro100_*_back.csv</i>, <i>*_fwd.csv</i>, <i>*_real.csv</i>) и "
        "файл сессии <i>session.json</i>. CSV можно открывать в Excel."
    ))
    s.append(p("Настройки", H3))
    s.append(p("Те же поля что в мастере первого запуска, плюс:"))
    s.append(kv_table([
        ["Поле", "Назначение"],
        ["MT5 install dir",
         "Папка с terminal64.exe. Меняется только если вы переустановили MT5"],
        ["Project (home) dir",
         "Папка пользователя. Нужна чтобы найти MT5 Common\\Files. "
         "Менять не нужно"],
        ["Results dir",
         "Куда складывать выходные CSV и PDF. Пустое = AppData по умолчанию"],
        ["EA .ex5 path",
         "Путь к скачанному советнику. Меняется при выходе новой версии"],
        ["Telegram post URL",
         "Канал с советником. Меняется только при изменении канала разработчиками"],
    ]))
    s.append(p("Кнопки", H3))
    s.append(p(
        "<b>Сохранить настройки</b> -- записать все поля в settings.json и "
        "применить изменения сразу.<br/><b>Проверить EA против Telegram-поста</b> -- "
        "программа сходит в Telegram, прочитает имя файла из поста, сравнит "
        "с вашим. Покажет <b>[OK]</b> или <b>[WARNING]</b> -- в последнем "
        "случае скачайте свежий .ex5 из канала."
    ))

    # ====== Page 8: Output PDF anatomy ======
    s.append(PageBreak())
    s.append(p("7. Что внутри выходного PDF", H2))
    s.append(p(
        "После успешного прогона вы получаете PDF из нескольких страниц -- "
        "по одной на каждый таймфрейм, который участвовал в прогоне. Шапка "
        "страницы:"
    ))
    s.append(code(
        "XAUUSD  TF M5   Min depo 10000   Forward 2025.05.01 -- 2026.01.01"
    ))
    s.append(p(
        "Под шапкой -- таблица из 7 колонок. Первые пять -- данные тестера, "
        "две последние -- интерактивные поля, в которые можно писать прямо "
        "в PDF (через Edge / Adobe Reader / Foxit -- Chrome НЕ сохраняет "
        "введенные значения, его не используйте)."
    ))
    s.append(p("Колонки таблицы", H3))
    s.append(kv_table([
        ["Колонка", "Что означает"],
        ["Rating",
         "Сводный рейтинг от тестера. Чем выше -- тем лучше сетап на "
         "конкретном периоде. Сортировка таблицы по убыванию Rating"],
        ["Annual gmean %",
         "Геометрическая средняя годовая доходность в процентах. Главный "
         "показатель прибыльности сетапа в долгую"],
        ["Max rel DD %",
         "Максимальная относительная просадка в процентах. Чем ниже тем "
         "лучше. Если 100 -- сетап сливал в нуль; такие отсеяны еще на "
         "уровне фильтра top-N"],
        ["Trades",
         "Количество сделок за период форварда. Меньше 20 -- статистики "
         "мало, к таким сетапам относитесь с осторожностью"],
        ["Setup No",
         "Идентификатор сетапа в советнике. По нему вы потом подаете "
         "сетап на тестирование или в живую торговлю (см. п. 8)"],
        ["Check",
         "Интерактивный чекбокс. Поставьте галку рядом с сетапами, "
         "которые планируете запускать в работу"],
        ["Note",
         "Интерактивное текстовое поле. Произвольная заметка -- ваши "
         "комментарии, ссылки, что угодно"],
    ]))
    s.append(tip(
        "Чекбоксы и заметки сохраняются прямо в PDF -- следующий раз "
        "открыв файл вы увидите свои отметки. Это удобно когда вы "
        "постепенно отбираете сетапы из разных прогонов."
    ))

    # ====== Page 9: Using results ======
    s.append(PageBreak())
    s.append(p("8. Как использовать результаты дальше", H2))
    s.append(p(
        "Выходной PDF -- это короткий список из ~57 строк на TF, "
        "отсортированных по Rating. Это кандидаты, которые показали себя "
        "хорошо на forward-периоде. Дальше вы выбираете из них что "
        "действительно использовать."
    ))
    s.append(p("Проверка отдельного сетапа в тестере MT5", H3))
    s.append(p(
        "1. Запишите номер сетапа из колонки <b>Setup No</b> того кандидата, "
        "который вам понравился (например 374521)."
    ))
    s.append(p(
        "2. Откройте MT5 (любой -- хоть тот же что был под тесты, хоть "
        "ваш основной), Strategy Tester (Ctrl+R)."
    ))
    s.append(p(
        "3. Выберите советник <i>XaurusPro100MK2_tst_009</i>, символ "
        "и TF из шапки PDF-страницы (например XAUUSD, M5)."
    ))
    s.append(p(
        "4. В разделе Inputs найдите параметр <b>inp_set</b> -- введите туда "
        "ваш номер сетапа (положительное число)."
    ))
    s.append(p(
        "5. Период тестирования -- любой который хотите проверить "
        "(например год после forward-окна). Запустите кнопкой Start."
    ))
    s.append(p(
        "Результат -- график equity для этого конкретного сетапа на новом "
        "периоде. Если сетап продолжает расти -- хороший кандидат на live. "
        "Если просел -- forward-результат был случайностью."
    ))
    s.append(p("Запуск в живую торговлю", H3))
    s.append(p(
        "1. Скачайте обычную (НЕ _tst) версию советника из канала: "
        "<i>XaurusPro100MK2_009.ex5</i> -- она для живых чартов."
    ))
    s.append(p(
        "2. Поставьте советник на нужный график в основном торговом "
        "терминале. В Inputs -- тот же <b>inp_set</b> с номером сетапа из PDF, "
        "плюс размер счета, размер позиции (<b>inp_mm</b>) и прочие настройки "
        "под ваш стиль."
    ))
    s.append(warn(
        "Pro100GUI выдает кандидатов, но не гарантирует прибыль в будущем. "
        "Forward-результат -- это <i>прошедший</i> период, future performance "
        "может отличаться. Используйте размер позиции, который не страшно "
        "потерять, и следите за просадкой первые недели live-торговли."
    ))
    s.append(p("Сравнение прогонов", H3))
    s.append(p(
        "Сделав несколько прогонов с разными конечными датами или разными "
        "TF, вы получите несколько PDF в папке результатов. Сетапы, которые "
        "встречаются в топе разных прогонов -- более устойчивые кандидаты "
        "(меньше шанс что это случайный выброс)."
    ))

    # ====== Page 10: Resume + troubleshooting ======
    s.append(PageBreak())
    s.append(p("9. Возобновление и решение проблем", H2))
    s.append(p("Возобновление прерванной сессии", H3))
    s.append(p(
        "Pro100GUI после каждой завершенной фазы сохраняет состояние в "
        "<i>session.json</i>. Если в процессе прогона:"
    ))
    s.append(p(" - выключили компьютер;"))
    s.append(p(" - случилось внезапное отключение питания;"))
    s.append(p(" - завис MetaTrader и его пришлось убить через Task Manager;"))
    s.append(p(" - случайно закрыли Pro100GUI;"))
    s.append(p(
        "-- то при следующем запуске программы сразу появится диалог "
        "<b>Незавершенная сессия</b> с информацией о прогрессе и тремя "
        "кнопками:"
    ))
    s.append(kv_table([
        ["Кнопка", "Действие"],
        ["Продолжить",
         "Возобновляет прогон с прерванной фазы. Уже сделанные фазы "
         "пропускаются. Это самый частый выбор"],
        ["Новая сессия",
         "Открывает вкладку Конфигурация -- сделайте новый прогон с нуля. "
         "Старая сессия остается в файлах, но больше не предлагается"],
        ["Отмена",
         "Ничего не делать. Диалог снова появится при следующем запуске"],
    ]))
    s.append(p("Что делать если фаза упала с ошибкой", H3))
    s.append(p(
        "1. Посмотрите колонку <b>Notes</b> -- там краткое описание (например "
        "<i>terminal exit=3</i> или <i>pro100.csv not produced</i>)."
    ))
    s.append(p(
        "2. Откройте лог тестера: указанная в Настройках папка MT5 -> "
        "<i>Tester\\Agent-127.0.0.1-3000\\logs\\</i> -> файл сегодняшней даты. "
        "Внизу будут реальные ошибки MetaTrader."
    ))
    s.append(p(
        "3. Самые частые причины:"
    ))
    s.append(p(
        "   - <b>не загружена история по символу</b>. Откройте MT5 вручную, "
        "загрузите бары для XAUUSD на нужном TF (Service -> "
        "Download history)."
    ))
    s.append(p(
        "   - <b>советник устарел</b>. Кликните в Настройках "
        "<b>Проверить EA</b>. Если WARNING -- скачайте новую версию."
    ))
    s.append(p(
        "   - <b>места на диске недостаточно</b>. Каждая фаза тестера "
        "может выгрузить десятки гигабайт в Tester cache MT5."
    ))
    s.append(p("Удаление программы", H3))
    s.append(p(
        "Пуск -> Параметры -> Приложения -> Pro100GUI -> Удалить. Или "
        "Пуск -> Pro100GUI -> Uninstall. Папка с настройками "
        "(<i>%AppData%\\Pro100GUI</i>) остается -- удалите ее вручную "
        "если не планируете возвращаться."
    ))
    s.append(p("Поддержка", H3))
    s.append(p(
        "Все вопросы и сообщения об ошибках -- "
        "<b>https://github.com/A-traders/Pro100GUI/issues</b>"
    ))

    return s


def build():
    out = Path(__file__).parent / "UserGuide.pdf"
    doc = BaseDocTemplate(
        str(out), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="Pro100GUI -- руководство пользователя",
        author="atradersteam",
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height, id="main",
    )
    doc.addPageTemplates([
        PageTemplate(id="all", frames=[frame], onPage=header_footer),
    ])
    doc.build(build_story())
    print(f"PDF written: {out}")
    return out


if __name__ == "__main__":
    build()
