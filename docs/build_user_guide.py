"""Сборка docs/UserGuide.pdf -- руководство пользователя.

Используется reportlab Platypus + Arial для поддержки кириллицы.
Запуск:
    python docs/build_user_guide.py
Результат:
    docs/UserGuide.pdf
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
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

# Make <b>...</b> / <i>...</i> use Bold/Italic.
from reportlab.pdfbase.pdfmetrics import registerFontFamily

registerFontFamily(
    "Body", normal="Body", bold="Bold", italic="Italic",
    boldItalic="Bold",
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
    textColor=colors.HexColor("#1a237e"), spaceBefore=18, spaceAfter=8,
    leading=19,
)
H3 = ParagraphStyle(
    "H3", parent=BASE["Heading3"], fontName="Bold", fontSize=12,
    textColor=colors.HexColor("#283593"), spaceBefore=10, spaceAfter=4,
    leading=15,
)
BODY = ParagraphStyle(
    "BODY", parent=BASE["BodyText"], fontName="Body", fontSize=10.5,
    leading=14, spaceAfter=6, alignment=TA_LEFT,
)
CODE = ParagraphStyle(
    "CODE", parent=BASE["Code"], fontName="Mono", fontSize=9.5,
    leading=13, leftIndent=12, spaceBefore=4, spaceAfter=8,
    backColor=colors.HexColor("#f4f4f4"), borderPadding=6,
    borderColor=colors.HexColor("#d0d0d0"), borderWidth=0.5,
)
NOTE = ParagraphStyle(
    "NOTE", parent=BODY, leftIndent=10, rightIndent=10,
    backColor=colors.HexColor("#fff8e1"), borderColor=colors.HexColor("#ffb300"),
    borderWidth=0.5, borderPadding=8, spaceBefore=6, spaceAfter=10,
    textColor=colors.HexColor("#5d4037"),
)
WARN = ParagraphStyle(
    "WARN", parent=NOTE,
    backColor=colors.HexColor("#ffebee"), borderColor=colors.HexColor("#c62828"),
    textColor=colors.HexColor("#b71c1c"),
)

# ---------- helpers ----------

def p(text: str, style=BODY):
    return Paragraph(text, style)

def code(text: str):
    # Escape angle brackets for reportlab Paragraph.
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe = safe.replace("\n", "<br/>")
    return Paragraph(safe, CODE)

def note(text: str):
    return Paragraph("<b>Подсказка.</b> " + text, NOTE)

def warn(text: str):
    return Paragraph("<b>Внимание.</b> " + text, WARN)

def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Body", 8)
    canvas.setFillColor(colors.HexColor("#888888"))
    # Footer: page number
    canvas.drawRightString(
        A4[0] - 15 * mm, 12 * mm,
        f"Pro100GUI -- руководство пользователя  |  стр. {doc.page}",
    )
    canvas.restoreState()

# ---------- content ----------

def build_story():
    story = []

    # ========== Title ==========
    story.append(Spacer(1, 30 * mm))
    story.append(p("Pro100GUI", H1))
    story.append(p(
        "Руководство пользователя по установке и работе с программой",
        ParagraphStyle("subtitle", parent=BODY, fontSize=14, leading=18,
                      textColor=colors.HexColor("#283593"), spaceAfter=20),
    ))
    story.append(Spacer(1, 6 * mm))
    story.append(p(
        "Pro100GUI -- это десктоп-приложение, которое автоматизирует прогон "
        "стратегического тестера MetaTrader 5 для пайплайна Pro100. "
        "Программа выполняет последовательно фазы оптимизации (BACK), "
        "форвард-теста (FORWARD) и при желании прогон по реальным тикам (REAL) "
        "для нескольких таймфреймов, после чего собирает итоговый PDF-отчёт "
        "с лучшими сетапами."
    ))
    story.append(p(
        "Документ рассчитан на пользователя, который умеет работать с Windows "
        "(скачать архив, запустить установщик), но не обязательно знаком с "
        "Python, командной строкой или git."
    ))
    story.append(Spacer(1, 6 * mm))
    story.append(p("Содержание", H3))
    toc = [
        "1. Что нужно установить заранее",
        "2. Установка Python",
        "3. Скачивание Pro100GUI",
        "4. Скачивание советника из Telegram",
        "5. Первый запуск",
        "6. Настройка путей и проверка советника",
        "7. Запуск прогона",
        "8. Просмотр результатов и возобновление",
        "9. Если что-то пошло не так",
    ]
    for line in toc:
        story.append(p(line))

    # ========== Page 2: Prerequisites ==========
    story.append(PageBreak())
    story.append(p("1. Что нужно установить заранее", H2))
    story.append(p(
        "На вашем компьютере должны быть три вещи:"
    ))
    prereq = Table(
        [
            ["Компонент", "Где взять", "Размер"],
            ["Python 3.11+", "https://www.python.org/downloads/", "~30 МБ"],
            ["MetaTrader 5", "Сайт вашего брокера", "~500 МБ"],
            ["Pro100GUI", "https://github.com/A-traders/Pro100GUI", "~5 МБ"],
            ["Советник .ex5", "https://t.me/xauruspro/16", "~220 КБ"],
        ],
        colWidths=[40 * mm, 80 * mm, 25 * mm],
    )
    prereq.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Body", 10),
        ("FONT", (0, 0), (-1, 0), "Bold", 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eaf6")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdbdbd")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(prereq)
    story.append(Spacer(1, 4 * mm))
    story.append(p(
        "Версия Windows -- 10 или 11. Программа теоретически работает и "
        "на старших версиях, но мы её там не тестировали."
    ))
    story.append(note(
        "Если MetaTrader 5 у вас уже установлен и вы оттуда торгуете -- "
        "оставляйте всё как есть. Pro100GUI не вмешивается в ваш основной "
        "терминал. Тесты он запускает в режиме portable и не трогает "
        "ваши настройки символов."
    ))

    # ========== Page 3: Python ==========
    story.append(PageBreak())
    story.append(p("2. Установка Python", H2))
    story.append(p(
        "Откройте в браузере <b>https://www.python.org/downloads/</b> -- "
        "увидите большую жёлтую кнопку <b>Download Python 3.13.x</b> "
        "(точная версия может отличаться, главное чтобы было 3.11 или новее)."
    ))
    story.append(p(
        "Кликните по ней, дождитесь скачивания (~30 МБ), запустите "
        "установщик (это файл <i>python-3.13.x-amd64.exe</i> в "
        "Загрузках)."
    ))
    story.append(warn(
        "В первом окне установщика обязательно поставьте галочку "
        "<b>Add python.exe to PATH</b> -- она внизу слева. Без неё "
        "Pro100GUI потом не сможет найти Python."
    ))
    story.append(p(
        "После галочки нажмите <b>Install Now</b>. Установка ~1 минута. "
        "В конце нажмите <b>Close</b>."
    ))
    story.append(p("Проверка установки", H3))
    story.append(p(
        "Нажмите Win+R, введите <b>cmd</b>, Enter -- откроется командная "
        "строка. Наберите там команду и нажмите Enter:"
    ))
    story.append(code("python --version"))
    story.append(p(
        "Должна вывестись строка вида <b>Python 3.13.0</b>. Если вместо "
        "этого пишет <i>'python' не является внутренней или внешней "
        "командой</i> -- значит галочку <b>Add to PATH</b> вы пропустили. "
        "Запустите установщик ещё раз, выберите <b>Modify</b>, поставьте "
        "галочку, нажмите Next/Install."
    ))

    # ========== Page 4: Download Pro100GUI ==========
    story.append(PageBreak())
    story.append(p("3. Скачивание Pro100GUI", H2))
    story.append(p(
        "Откройте в браузере страницу проекта: "
        "<b>https://github.com/A-traders/Pro100GUI</b>"
    ))
    story.append(p(
        "Найдите справа сверху зелёную кнопку <b>&lt;&gt; Code</b>. "
        "Кликните по ней -- развернётся меню, в нём пункт <b>Download ZIP</b>. "
        "Скачайте архив (~5 МБ)."
    ))
    story.append(p(
        "Распакуйте архив в любую удобную папку, например <i>C:\\Pro100GUI\\</i>. "
        "Если делаете правый клик -> <b>Извлечь все...</b> -- то Windows "
        "распакует во вложенную папку <i>Pro100GUI-main\\</i>, это нормально."
    ))
    story.append(note(
        "Версия программы -- это просто файлы внутри архива. Когда выйдет "
        "обновление, скачайте новый ZIP и замените старую папку. Все ваши "
        "настройки лежат отдельно в <i>%APPDATA%\\Pro100GUI\\</i> и "
        "не пропадут."
    ))
    story.append(p("4. Скачивание советника из Telegram", H2))
    story.append(p(
        "Pro100GUI использует советник <i>XaurusPro100MK2</i>. Скачать его нужно "
        "вручную из официального публичного поста."
    ))
    story.append(p(
        "Откройте: <b>https://t.me/xauruspro/16</b>"
    ))
    story.append(p(
        "В посте есть прикреплённый файл с именем вида "
        "<i>XaurusPro100MK2_tst_009.ex5</i> (последняя версия может отличаться). "
        "Скачайте его -- через Telegram Desktop или из веб-версии. "
        "Сохраните в любое место, например в ту же папку с Pro100GUI."
    ))
    story.append(warn(
        "Это единственный официальный источник советника. Не скачивайте "
        ".ex5 с других сайтов. Pro100GUI при запуске сверяет имя файла "
        "с тем, что лежит в этом канале -- и предупредит, если у вас "
        "устаревшая версия."
    ))

    # ========== Page 5: First launch ==========
    story.append(PageBreak())
    story.append(p("5. Первый запуск", H2))
    story.append(p(
        "Зайдите в папку, куда распаковали Pro100GUI. Найдите файл "
        "<b>Pro100GUI.pyw</b>. У него иконка зелёного питона."
    ))
    story.append(p("Двойной клик."))
    story.append(p(
        "При самом первом запуске откроется небольшое окно -- оно скачивает "
        "и устанавливает все необходимые библиотеки (PySide6, reportlab и "
        "ещё несколько). Это занимает 1-3 минуты в зависимости от скорости "
        "интернета. В сумме скачается около 150 МБ."
    ))
    story.append(p(
        "После установки откроется главное окно Pro100GUI с четырьмя "
        "вкладками:"
    ))
    tabs = Table(
        [
            ["Вкладка", "Назначение"],
            ["Конфигурация", "Настройка прогона: даты, символ, таймфреймы"],
            ["Прогон", "Живой прогресс, лог, кнопка Cancel"],
            ["Результаты", "Список готовых PDF-отчётов"],
            ["Настройки", "Пути к MT5 и советнику (это вы здесь зададите)"],
        ],
        colWidths=[45 * mm, 110 * mm],
    )
    tabs.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Body", 10),
        ("FONT", (0, 0), (-1, 0), "Bold", 10),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eaf6")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdbdbd")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tabs)
    story.append(Spacer(1, 4 * mm))
    story.append(p(
        "Если найдена незавершённая сессия (например, в прошлый раз вы "
        "закрыли программу посреди прогона), сразу при запуске появится "
        "диалог: <b>Продолжить / Новая сессия / Отмена</b>."
    ))
    story.append(note(
        "При <b>самом первом</b> запуске такого диалога не будет -- у вас "
        "ещё нет ни одной сохранённой сессии. Это нормально."
    ))

    # ========== Page 6: Settings ==========
    story.append(PageBreak())
    story.append(p("6. Настройка путей и проверка советника", H2))
    story.append(p(
        "Откройте вкладку <b>Настройки</b>. Заполните пять полей."
    ))
    story.append(p("MT5 install dir", H3))
    story.append(p(
        "Папка установки MetaTrader 5 (та, в которой лежит "
        "<i>terminal64.exe</i>). У большинства брокеров это что-то "
        "вроде:"
    ))
    story.append(code(r"C:\Program Files\RoboForex MT5 Terminal"))
    story.append(p(
        "Кликните <b>...</b> справа и выберите папку через диалог."
    ))
    story.append(p("Project (home) dir", H3))
    story.append(p(
        "Корневая папка вашего пользователя -- по умолчанию <i>C:\\Users\\Имя_пользователя</i>. "
        "Нужна чтобы найти общую папку MT5 (Common\\Files). "
        "Скорее всего менять не придётся."
    ))
    story.append(p("Results dir", H3))
    story.append(p(
        "Куда складывать готовые CSV и PDF. Можно оставить пустым -- тогда "
        "Pro100GUI будет писать в <i>%APPDATA%\\Pro100GUI\\results\\</i>. "
        "Или укажите свою папку."
    ))
    story.append(p("EA .ex5 path", H3))
    story.append(p(
        "Путь к скачанному из Telegram файлу советника. Кликните <b>...</b>, "
        "выберите файл <i>XaurusPro100MK2_tst_009.ex5</i>."
    ))
    story.append(p("Telegram post URL", H3))
    story.append(p(
        "Адрес поста с советником. По умолчанию заполнен -- "
        "<i>https://t.me/xauruspro/16</i>. Менять не надо."
    ))
    story.append(p("Проверка", H3))
    story.append(p(
        "Внизу нажмите <b>Сохранить настройки</b>, затем "
        "<b>Проверить EA против Telegram-поста</b>. Программа загрузит "
        "пост из Telegram, сравнит имя вашего файла с опубликованным, "
        "и выведет одно из:"
    ))
    story.append(p(
        "<b>[OK]</b> -- ваш файл соответствует последней публикации. Готовы к работе."
    ))
    story.append(p(
        "<b>[WARNING]</b> -- имя расходится. Скачайте свежий .ex5 из канала, "
        "обновите путь, проверьте ещё раз."
    ))

    # ========== Page 7: Run ==========
    story.append(PageBreak())
    story.append(p("7. Запуск прогона", H2))
    story.append(p("Перейдите на вкладку <b>Конфигурация</b>. Заполните параметры."))
    story.append(p("End date", H3))
    story.append(p(
        "Дата конца прогона -- последний день, который попадёт в FORWARD. "
        "Программа сама посчитает back/forward окна от этой даты с учётом "
        "галки <b>Snap dates to 1st of month</b> (по умолчанию включено)."
    ))
    story.append(p("Symbol / Min depo", H3))
    story.append(p(
        "Символ -- по умолчанию <i>XAUUSD</i>. Депозит в счёте теста -- "
        "по умолчанию 10 000."
    ))
    story.append(p("Snap dates / Run REAL phase", H3))
    story.append(p(
        "Первая галка -- округлять даты к первому числу месяца. Обычно "
        "оставляют включённой. Вторая -- запускать ли финальный прогон "
        "по реальным тикам для топ-сетапов. Это +час-два на прогон, но "
        "результаты ближе к реальной торговле."
    ))
    story.append(p("Timeframe plans", H3))
    story.append(p(
        "Таблица: какие таймфреймы тестировать и на каких окнах в месяцах. "
        "По умолчанию 5 строк: M1 (3/6), M5 (4/8), M15 (5/10), M30 (6/12), "
        "H1 (8/16). Можно добавить/удалить строки кнопками внизу таблицы."
    ))
    story.append(p(
        "Числа в Back / Forward -- месяцы. Forward всегда вдвое больше Back."
    ))
    story.append(p("Запуск", H3))
    story.append(p(
        "Кнопка <b>Start</b> внизу. Программа автоматически переключится "
        "на вкладку <b>Прогон</b>."
    ))
    story.append(p(
        "Там виден список job-ов (по два на каждый TF: BACK и FORWARD, плюс "
        "PDF в конце), их статус, текущая длительность и количество строк "
        "в csv. Внизу -- скользящий лог."
    ))
    story.append(p(
        "Один прогон BACK -- от 30 минут до нескольких часов в зависимости "
        "от TF и окна. M1 BACK 3 месяца -- около часа. H1 BACK 8 месяцев -- "
        "минут 20."
    ))
    story.append(p(
        "Если нужно прервать -- кнопка <b>Cancel</b> справа сверху. Текущая "
        "фаза доработает до конца, остальные пометятся SKIPPED. Сессию "
        "потом можно продолжить с этого места."
    ))
    story.append(warn(
        "Пока идёт прогон -- не запускайте отдельно MetaTrader 5 в том же "
        "терминале, что указан в настройках Pro100GUI. Программа "
        "автоматически проверяет, что terminal64.exe не запущен, и отказывается "
        "стартовать если он уже работает."
    ))

    # ========== Page 8: Results + troubleshooting ==========
    story.append(PageBreak())
    story.append(p("8. Просмотр результатов и возобновление", H2))
    story.append(p("Результаты прогона", H3))
    story.append(p(
        "По завершении вкладка <b>Результаты</b> обновится -- появится "
        "файл <i>Pro100_&lt;идентификатор_сессии&gt;.pdf</i>. Двойной клик "
        "по нему открывает PDF в системном просмотрщике."
    ))
    story.append(p(
        "Кнопка <b>Open results folder</b> открывает папку с результатами "
        "в Проводнике -- там же лежат отдельные csv по каждой фазе и "
        "файл сессии <i>session.json</i>."
    ))
    story.append(p("Возобновление прерванной сессии", H3))
    story.append(p(
        "Pro100GUI после каждой завершённой фазы сохраняет состояние в "
        "<i>session.json</i>. Если в процессе прогона:"
    ))
    story.append(p("- выключили компьютер;"))
    story.append(p("- упало электричество;"))
    story.append(p("- завис MetaTrader и его пришлось закрыть;"))
    story.append(p("- случайно закрыли Pro100GUI;"))
    story.append(p(
        "-- то при следующем запуске программа сама предложит "
        "<b>Продолжить</b>. Уже сделанные фазы будут пропущены, "
        "выполнение возобновится с прерванной."
    ))
    story.append(p("9. Если что-то пошло не так", H2))
    story.append(p("Не запускается двойным кликом", H3))
    story.append(p(
        "Откройте командную строку (Win+R, cmd, Enter) и запустите "
        "программу через python (не pythonw) -- увидите детальную ошибку:"
    ))
    story.append(code("python C:\\Pro100GUI\\Pro100GUI.pyw"))
    story.append(p("Прогон падает на первой же фазе", H3))
    story.append(p(
        "Откройте лог терминала: указанный в настройках путь MT5 -> "
        "<i>Tester\\Agent-127.0.0.1-3000\\logs\\&lt;дата&gt;.log</i>. "
        "Там видны реальные ошибки MetaTrader."
    ))
    story.append(p("Советник устарел", H3))
    story.append(p(
        "Если проверка показывает <b>[WARNING]</b> -- зайдите в "
        "<i>https://t.me/xauruspro/16</i>, скачайте новый .ex5, обновите "
        "путь в настройках, проверьте снова."
    ))
    story.append(p("Тесты не проходят (для разработчиков)", H3))
    story.append(p(
        "Из командной строки в папке Pro100GUI:"
    ))
    story.append(code("python -m pytest tests/"))
    story.append(p(
        "Должно быть 233+ passed. Если меньше -- сообщите в issues "
        "на GitHub."
    ))

    return story


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
