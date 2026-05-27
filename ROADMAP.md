# Pro100GUI Roadmap

Single source of truth for project state and next steps. A fresh
Claude session (or human) should be able to pick up the work using
only:

1. This file.
2. The codebase (`git log` for history, `pytest` for state).
3. Memory entries `project_pro100gui*` for high-level context.

---

## Status (snapshot)

- **Repo**: <https://github.com/imyavel/Pro100GUI> (private).
- **Layers complete**: core / adapters / orchestrator / gui + app shell.
- **Tests**: 192 passing on Python 3.14 (`python -m pytest tests/`).
- **CI**: `no-ea-files` workflow green on every push to `main`.
- **Stack**: Python 3.11+, PySide6, reportlab, pypdfium2, pypdf, Pillow,
  requests. Bootstrap (`bootstrap.py`) installs missing deps on first run.
- **Entry point**: `pythonw Pro100GUI.pyw`.

### Completed milestones (one per commit on `main`)

1. Initial 5-layer scaffold + bootstrap + .pyw entry.
2. EA-leak safeguards (`.gitignore` + pre-commit hook + CI workflow).
3. Layer 1 core -- models, periods, filters, twr, pro100 csv codec.
4. Layer 2.1 -- TF table, .set + .ini builders.
5. Layer 2.2 -- MT5Paths, FilesStaging, TerminalRunner.
6. Layer 2.3 -- EAVersionChecker (Telegram embed parser).
7. Layer 2.4 -- EARegistry (symbolic build keys).
8. Layer 2.5 -- PdfRenderer (v005 layout) + PdfQC.
9. Layer 3 -- EventBus, SessionState (JSON-persisted), Orchestrator.
10. Layer 4 -- PySide6 main window with 4 screens + Qt worker thread.
11. Resume UI -- startup dialog offering to continue an unfinished session.

---

## Architectural decisions (compact log)

These are the choices that aren't obvious from the code alone.

- **Stack: PySide6 over tkinter**. Initially considered tkinter (zero
  deps), settled on PySide6 because the app already pulls in
  reportlab + pypdfium2 + Pillow + requests, so the extra 80 MB is a
  small marginal cost for substantially better widgets. Bootstrap
  installs PySide6 on first run.
- **EA source: manual download + filename check, NOT auto-fetch**.
  User downloads `.ex5` from <https://t.me/xauruspro/16> and points
  the GUI at the local file. `EAVersionChecker` reads the embed page
  of that post and compares the filename. Reasons: no Telegram
  credentials needed (Bot API / Telethon would require API_ID +
  phone-code auth); the EA is rarely updated; manual download keeps
  the GUI's network footprint to one tiny HTTP GET.
- **Naming convention**: `_NNN` suffix from CLAUDE.md is **not used**
  in this project. Versions = git commits. CLAUDE.md was written
  before this repo existed.
- **MM-sweep deferred until EA _009**. The currently-published EA
  (`XaurusPro100MK2_tst_008.ex5`) has hardcoded AddFr filter
  constants that prevent the "3rd-pass after fail" algorithm used in
  MM-sweep. Plan: delegate `mql-dev` agent to produce `_009` that
  reads AddFr constants from a config file the GUI writes alongside
  `pro100.csv`. Until then GUI only supports BACK / FWD / REAL phases.
- **9-column merged PDF deferred** (same reason -- depends on MM-sweep).
  Current renderer ports the v005 layout (5 data columns + Check +
  Note AcroForm fields).
- **Threading**: Orchestrator runs on a QThread; events flow back to
  GUI via Qt signals (auto-marshaled across threads).
- **Persistence**: SessionState is rewritten as JSON after every
  phase, so a crashed run can resume. AppSettings (paths, EA file,
  Telegram URL) lives under `%APPDATA%\Pro100GUI\settings.json`.
- **Resume UX: startup dialog, not a sidebar button**. On launch
  MainWindow checks `settings.last_session_path`; if the file
  exists and has PENDING/RUNNING jobs, a QMessageBox offers
  Resume / New / Cancel. This is the only resume entry point --
  there is no "Resume" button on the Run tab. Reason: a button
  would imply resume is normal flow; in practice it only matters
  after a crash or forced shutdown, so a startup question is the
  natural touchpoint.
- **Three rubejs against EA-file leak**: `.gitignore` ignores
  `.mq5/.ex5/.mqh/.set/.ini/.tst`; `tools/hooks/pre-commit` rejects
  staged files with those extensions at commit time; the
  `.github/workflows/no-ea-files.yml` CI scans `git ls-files` on
  every push.

---

## Module map

```
pro100gui/
├── core/                       # Layer 1 -- pure logic, no I/O
│   ├── models.py               #   RunConfig / TFPlan / DateWindow / AddFrMode / TF
│   ├── periods.py              #   compute_periods (snap-to-month-start)
│   ├── filters.py              #   Pro100Row, filter_top_n_dd, third_pass_after_fail
│   ├── twr.py                  #   twr_year, months_to_x, format_twr
│   ├── pro100_csv.py           #   UTF-16 LE BOM read/write
│   └── tf.py                   #   TF string/minutes/enum table
│
├── adapters/                   # Layer 2 -- external systems
│   ├── paths.py                #   MT5Paths (install + derived dirs)
│   ├── set_file.py             #   FixedParam/RangeParam + back/fwd/real/mm_sweep presets
│   ├── ini_file.py             #   IniConfig + TesterModel/OptimizationMode enums
│   ├── files_staging.py        #   stage_ea / write_set / write_ini / pro100 io
│   ├── terminal_runner.py      #   is_running watchdog + run() with subprocess
│   ├── ea_version_checker.py   #   Telegram embed parser + check(local_path)
│   ├── ea_registry.py          #   EABuild + EARegistry, TESTER_BUILD / OPT_BUILD keys
│   ├── pdf_renderer.py         #   PageSpec + PdfRenderer (v005 layout)
│   └── pdf_qc.py               #   render_pages_to_png via pypdfium2
│
├── orchestrator/               # Layer 3 -- pipeline coordination
│   ├── events.py               #   Event types + EventBus + EventRecorder
│   ├── session.py              #   JobSpec/Status/Phase, SessionState + save/load
│   └── orchestrator.py         #   run/resume/cancel + per-phase execution
│
├── gui/                        # Layer 4 -- PySide6
│   ├── main_window.py          #   Builds adapter stack, hosts 4 tabs
│   ├── worker.py               #   OrchestratorWorker (QThread + signals)
│   ├── screen_config.py        #   Config form + TF-plan table
│   ├── screen_run.py           #   Job tree + log + cancel
│   ├── screen_results.py       #   PDF list with system-open
│   └── screen_settings.py      #   Paths + EA picker + verify button
│
└── app/                        # Layer 5 -- shell
    ├── main.py                 #   QApplication entry point
    └── settings_store.py       #   AppSettings + JSON load/save
```

---

## Next steps (prioritized)

1. **Pytest-qt-based GUI tests** (~half-day).
   Smoke-test each screen's interaction without real MT5: config
   form -> Start -> verify worker is spawned with the right config;
   resume dialog -> Resume -> verify worker.resume_run called; etc.
2. **EA _009 delegation to mql-dev** (~external).
   See `project_pro100gui_ea_v009.md` memory. Out of scope for this
   project until the new EA is published in the Telegram channel.
3. **MM-sweep wiring + 9-column PDF** (~1-2 days, after EA _009).
   Adds:
   - `FilesStaging.write_addfr_config(dname, profile)` to put the
     constants file next to `pro100.csv` before each phase.
   - New PdfRenderer mode for the v013 layout (TWR / Mo-to-x11 /
     dup-paired highlight).
   - `merge_v005_v009` in core (currently deferred).
4. **EA download automation** (optional, ~half-day).
   Could replace manual download with Telethon if user later
   provides API_ID/HASH. Currently a deliberate "no" -- documented
   above.
5. **Cross-machine portability** (optional).
   `MT5Paths` defaults assume the developer's machine layout.
   For other users, the Settings screen already exposes both paths;
   no code change needed unless we want auto-detect heuristics.
6. **PyInstaller .exe packaging** (NOT recommended without code signing).
   A single-file .exe removes the Python-install step, but an
   unsigned exe triggers SmartScreen at first run. Removing that
   warning needs an EV code-signing certificate (~$300-700/year +
   USB token + company verification). The current `.pyw` runs under
   the PSF-signed `pythonw.exe`, so SmartScreen is silent. Park
   this item until either signing is available or the Python
   prerequisite becomes a real complaint.

---

## Continuing in a fresh Claude session

1. Memory entry `project_pro100gui.md` points here.
2. Read this file end-to-end first.
3. Verify status: `cd C:\Users\Администратор\Pro100GUI && python -m pytest tests/`
   should still report 192 passed.
4. If the user named a specific next step (e.g. "let's do the
   PyInstaller package"), jump directly to that section above.
   If they said "continue", ask which of the prioritized next steps
   to tackle first.
