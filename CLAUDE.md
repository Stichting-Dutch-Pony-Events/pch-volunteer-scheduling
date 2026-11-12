# CLAUDE.md: agreements and context for this project

This file is for any Claude (Code) session working on this repository. Read it fully
before doing anything.

**Also read `ReferenceDocuments/DATA_NOTES.md` if it exists.** It holds notes about the
real volunteer data and is kept out of git for privacy.

## What this is

A tool to automate the volunteer schedule of **PonyCon Holland**, a 3-day convention
(Friday afternoon to Sunday evening) with about 40 volunteers and 20-30 posts.
Making the schedule by hand takes the volunteer manager about 3 days.

The volunteer manager is good with Python and wants to **follow along and understand
the code**. Explain, keep code plain and well commented, no clever tricks.
The user is also using this project to get reacquainted with Python and TDD, and
likes to write tests (and often code) themselves; Claude reviews and explains.

## How we work (agreed, please follow)

1. **Say what you will do before doing it, and wait for an OK.** Take it slow,
   one small step at a time.
   *Exception:* `CLAUDE.md` and `ReferenceDocuments/DATA_NOTES.md` may be updated
   without asking. Keep them current when agreements, decisions or status change.
   Anything privacy-sensitive (about specific people) goes in DATA_NOTES.md, never here.
   **Keep the README Status in sync** with the roadmap below (a short version, without
   implementation details) whenever a roadmap item is done or the roadmap changes.
   **Code in `scheduler/` and `tests/`: only suggest it, the user types it in.** Then
   review their file when asked.
2. **Test-driven development.** For every step:
   tests first and let the user read them, run them and see them fail (red),
   then just enough code to pass (green), tidy up, the user commits.
3. **Every test uses `# Arrange`, `# Act`, `# Assert` comments**, even when a section
   is empty (write a short comment saying why). Keep Act and Assert on separate lines
   (`result = f()` then `assert result == ...`). One behaviour per test, a name that
   reads like a sentence, a one-line docstring.
   **Tests that depend on settings pass them explicitly** (never rely on the defaults in
   model.py): e.g. `RULES = Settings(60, 180, 30)` at the top of
   test_solver_work_stretches.py, names say "the minimum/maximum" rather than a number.
   The defaults themselves are pinned by `test_default_settings_match_the_agreed_rules`
   in test_model.py. Use concrete numbers in test data; don't compute it from settings.
   **Expected results are built with loops over concrete ranges** (user, 2026-11-04),
   e.g. `for block in range(0, 4): expected[("Tickets", 1, block)] = "Mock Mane"`,
   not written out entry by entry.
   **Workflow for new tests (agreed 2026-11-02):** Claude suggests tests, the user
   approves them, then Claude writes the test stubs in the test file: name, one-line
   docstring, empty `# Arrange` / `# Act` / `# Assert` sections, and
   `pytest.skip("not written yet")` as the last line, under `# Assert`. The user fills
   in each test and removes its skip line (then sees it go red). Code stubs in
   `scheduler/` raise `NotImplementedError`.
4. **The user handles version control** in VS Code / Sourcetree.
   Do not commit, push, branch or run other git commands that change state, unless the
   user specifically asks for that one action (confirmed 2026-11-05). Suggest a
   commit message when a step is done. Read-only git commands (status, log, branch) are fine.
   **Branches (agreed 2026-11-01):** `main` = working versions (merge at milestones such
   as version 1.0, maybe tag `v1.0`). `develop` = everyday work; small one-session steps
   go straight on it. Bigger steps that take several sessions get a short-lived feature
   branch from `develop` (e.g. `feature/workbook-reader`, `feature/output-excel`,
   `feature/window-app`), merged back once done and green, then deleted. The first one
   is the workbook reader. When starting a bigger step, remind the user to make the branch.
5. **Python only.** Python **3.14** in `.venv` (OR-Tools has no 3.15 wheels yet).
   Use the newer lowercase OR-Tools API (`new_int_var`, `add`, `solve`, `value`).
   **Type hints on every function we write from now on** (agreed 2026-11-01): all
   parameters and the return type, e.g. `def solve(problem: Problem) -> Schedule:`.
   Tests are the exception (no hints needed on `test_...` functions). Older functions
   without hints get them when we touch them anyway.
   **Line length: soft limit of 100 characters** (not PEP 8's 79). The user has a
   ruler at 100 in their local `.vscode/settings.json` (not in git), which also sets
   `files.eol` to CRLF and trims trailing whitespace on save.
6. Files use **Windows line endings (CRLF)**; keep them that way when editing. A
   Linux-based shell can show line-ending noise in `git status` (e.g. LICENSE) that is
   not a real change; use `git -c core.autocrlf=true status`.
7. The `.venv` is a Windows venv: the user runs the tests in VS Code
   (`python -m pytest`), not from a Linux shell.
8. **Never run the scheduler on real data without the user's explicit permission each
   time** (user, 2026-11-05; kept 2026-11-08 although a run now takes ~14 s): real data
   means the 2026 draft and any other real input, e.g. data from other conventions. The
   user wants to stay in control of those runs. The test suite and the test workbook
   are fine. **After every real-data run** (PCH or UKPC), run with `--debug-time` and add
   the times per step to `ReferenceDocuments/RUN_TIMES.md` (not in git; user, 2026-11-12).
   `ReferenceDocuments/time_runs.py` does several runs and averages each step.

## Privacy (important)

**Currently handling privacy data (user, 2026-11-08): the UKPC26 conversion.** Be extra
cautious: write progress, findings and decisions about that data **only** in
`ReferenceDocuments/DATA_NOTES.md`, never here, in the README, in code, tests, commit
messages or anywhere else in the repo. Here at most a one-line status without details.

The repo is on GitHub (`Stichting-Dutch-Pony-Events/pch-volunteer-scheduling`, GPL-3.0).
It is currently private, but **always treat it as public**. The user asked to be warned
whenever they are (or might be) putting privacy-sensitive data into the repo: check
`git status` / new files when relevant, and speak up rather than assume it's fine.

**No real volunteer data in git**: no form answers (they contain e-mail
addresses and real names), no schedules with nicknames, no notes about specific people.
`.gitignore` excludes `ReferenceDocuments/` and all `.ods`, `.xlsx`, `.csv` (except
`tests/data/**`). Tests use small **made-up** examples only.

Fictional nicknames for tests and examples (never use real nicknames):
**Mock Mane, Testy Hooves, Dummy Dash, Sample Sparkle, Placeholder Pip.**

## Technology

- **OR-Tools CP-SAT** as solver: hard rules are constraints, soft rules are weighted
  penalties in the objective.
- **Solver layout:** `solve()` in solver.py stays a short table of contents (create
  variables, call the rules, run CP-SAT, read the schedule). Each hard rule is a function
  `add_<name>_rule(model, problem, works)` in `scheduler/rules.py` with a docstring
  stating the rule in plain words; adding a rule = one new function in rules.py + one
  line in `solve()`. Helpers used only inside rules.py start with `_`. Prefer plain
  loops over comprehensions (the user finds loops easier to read). Maybe split into
  hard/soft rule files later, once there are soft rules.
- **Decided: no Rule base class for now** (plain functions with the same arguments are
  enough). Revisit later: the user may want to switch rules on/off from the workbook,
  and soft rules need weights. Focus first on a minimal viable scheduler, then expand.
- **Type alias `Works`** in rules.py: `dict[tuple[str, str, int], cp_model.IntVar]`, the
  solver's yes/no variables keyed by (volunteer_name, post, block). Lives in rules.py
  (solver.py imports rules, so the other way round would be circular); solver.py uses
  `rules.Works`. Rules return `-> None`.
- **Shared helpers:** `_variables_of` in rules.py collects a volunteer's variables in a
  block range (used by every per-volunteer rule). `runs_of_consecutive_blocks` in
  model.py (public, tested in test_model.py) is used by `Schedule.work_stretches_of`
  and `_short_pieces`.
- **openpyxl** for reading/writing `.xlsx`. No pandas for now.
- **workbook.py layout** (agreed 2026-11-02): imports, constants and `WorkbookError` at
  the top, then `read_problem` (the table of contents), then the tab readers in the
  order it calls them, then the shared helpers. (Function order doesn't matter to
  Python: a function only has to exist when it is called.) A helper used by only one
  reader sits right after that reader (agreed 2026-11-11). **Splitting workbook.py**
  (one module per tab in `scheduler/reading/`, shared helpers in e.g. `cells.py`): not
  yet (~530 lines); do it with option B or when Events/Wishes are added, whichever
  comes first (Claude's advice, 2026-11-11).
- **pytest** for tests. Version 1.0 runs from the command line; later a small program
  with a window (see the roadmap).

## Repository layout

```
ReferenceDocuments/   (not in git) real data, DATA_NOTES.md, draft input workbook
scheduler/            model.py (data classes), solver.py, rules.py (hard rules),
                      workbook.py (reads the input workbook), output.py (writes the
                      output workbook), __main__.py (the command line, run with
                      `python -m scheduler`), helpers.py (debug_print), errors.py
                      (WorkbookError, NoScheduleFound and its children), checks.py
                      (checks before solving: check_problem)
tests/                test_helpers.py; data/test_input.xlsx (made-up workbook)
tests/model/          test_model.py, test_time_blocks.py (tests of model.py)
tests/solver/         test_solver_availability.py, test_solver_basics.py,
                      test_solver_work_stretches.py, test_solver_stay_at_post.py,
                      test_checks.py, test_solver_maximum_hours.py, test_warnings.py
tests/output/         test_assign_slots.py, test_write_helpers.py,
                      test_create_schedule_sheet.py, test_write_output.py (tests of
                      writing the output workbook)
tests/workbook/       test_celltext.py, test_availability.py, test_find_columns.py,
                      test_read_settings.py, test_read_volunteers.py,
                      test_read_posts.py, test_read_skills.py, test_read_demand.py,
                      test_read_problem.py (one test file per reader part)
tests/command_line/   test_main.py (tests of the command line)
templates/            VolunteerInput_template.xlsx: empty input workbook (all tabs and
                      headers, Settings with example values from PonyCon Holland 2026,
                      no volunteer data). In git: .gitignore allows `templates/*.xlsx`.
                      Every test folder has an empty __init__.py (like tests/ itself).
requirements.txt      ortools>=9.15, openpyxl>=3.1, pytest>=8.0, pycodestyle>=2.15
                      (style check: `python -m pycodestyle --max-line-length=100
                      scheduler tests`)
```

## Domain: how scheduling was done by hand

- A spreadsheet with half-hour rows and one column per post "slot", a volunteer nickname
  in each cell, grey = post closed. Columns were reused for other tasks and colours had
  mixed meanings. The new way: **one column per post, a number = people needed,
  empty = closed.**
- A check sheet summed per volunteer per half hour: +1 per post, +0.9 for a
  REALLY-want event, +0.5 for a like-to-attend event (capped at 0.9). 1 = fine,
  1.5/1.9 = working during a wished event, 2 = double booked. The tool replaces this.
- Volunteers belong to teams: Ticketing, Tech, Gopher, Drivers, Infobooth, Security.
- Who may do what used to be in the manager's head. Now a **Skills matrix**:
  empty = never, 1 = can, 2 = good at it / likes it, 3 = main role.
- Volunteers fill in a form (CSV export): nickname plus semicolon-separated events they
  "would like to attend" and "REALLY want to attend". Names in the form are messy, so
  the Volunteers tab has a "Form name contains" column to map them to nicknames.
  Idea for next year: prefix events in the form with a 3-letter code (e.g. GQA, MNK).

## Rules for the schedule

Hard (never broken):
- every post gets exactly the number of people needed at each time block
- only volunteers with a skill score for that post
- nobody in two places at once
- a **work stretch** (continuous work, also across posts) is at least
  `min_stretch_minutes` (60) and at most `max_stretch_minutes` (180).
  Exception (agreed, revised): a stretch shorter than the minimum is allowed only if
  it is spent at one post and covers exactly one short piece of that post's demand:
  a run of consecutive blocks in which the post needs at least k people (for some k)
  that is shorter than the minimum. Example: Tickets needs 2 in blocks 0-1 and 1 in
  blocks 2-7, so the second person may work just blocks 0-1. A post open only
  06:00-06:30 is the same case with k = 1. The whole piece goes to one person.
- a break between two work stretches is at least `min_break_minutes` (30) (in
  practice usually ~2 hours: the user aims for roughly 50% work, 50% play)
- these three limits are in `Settings` (model.py, in minutes; the solver divides by
  15) so other users can choose e.g. a 30 min minimum
- a meal break inside each meal window for everyone working around it
- availability per day; fixed shifts placed by hand are kept

Soft (weighted, tunable in Settings):
- avoid working during REALLY-want events (weight 100) and like-to-attend events (20)
- prefer higher skill scores
- prefer shifts of at most 120 min
- prefer shifts that start and end on the hour or half hour (soft so the user can
  deviate by 15 min when needed)
- prefer staying at one post for a whole work stretch (few post switches)
- avoid short stretches (the exception above): try to have them work elsewhere too
- spread hours fairly
- (later, maybe) Question vetting, Manestage clean and Sardine duty by the same person

Time: **15-minute blocks** (the event schedule uses 15 min). Times before the day
boundary (06:00) belong to the night after that convention day (Saturday 01:00 =
Saturday night). **Block 0 = 06:00, every day**, so even blocks fall on :00/:30.
For now blocks are plain integers within one day; how to handle several days is
still to decide. Night work exists (e.g. Saturday music night until 02:00, people
around until ~03:00). **Daylight saving time is ignored for now** (assume no clock
changes; in 2026 the switch to winter time made 02:00 happen twice). Possible future
improvement.

Meals: Saturday lunch 12:00-14:00, Saturday dinner 18:00-19:00, Sunday lunch 12:00-14:00.

## Input workbook format

Tabs: ReadMe, Settings, Volunteers, Posts, Skills, Events, Demand, Wishes, Fixed (there
is no separate Meals tab; the meal windows are rows in Settings).
The workbook has its own ReadMe tab explaining each tab. **Formatting (user,
2026-11-11):** header row coloured, everything below it white (no fixed fills; the
yellow "to check" cells of the draft are listed in DATA_NOTES.md instead). Kept: the
conditional formatting on Skills (green by score) and Demand (empty = grey = closed).
Note for openpyxl: a conditional-formatting fill needs `bgColor` as well as `fgColor`
(`PatternFill(fill_type="solid", fgColor=x, bgColor=x)`), otherwise Excel shows no
colour (LibreOffice does); fixed in all four workbooks on 2026-11-11.
Header row: post columns on Skills and Demand vertical (90 degrees), the other headers
of Volunteers, Posts, Events, Wishes and Fixed at 45 degrees; Settings and ReadMe
straight. Posts include e.g. Tickets, Infobooth, Vendorguarding,
AD Vendorhall guarding, Question vetting, Manestage clean, Sardine duty, Event setup
(Panel/Workshop room), Event assistance, Signing session, Ticket check (Manestage/
Stairs/Balcony), Driving, Security (several), GoH Security 1/2, Evening games,
Cleanup, Post-con cleanup and a few Friday-only posts.

## Roadmap

- [x] Project structure, .gitignore, README, venv, hello-world test
- [x] Step 1: minimal solver with in-code test data. Hard rules: demand met exactly,
      only qualified volunteers, no double booking; NoScheduleFound when infeasible
- [x] Step 2: work stretches (60-180 min, short-post exception) and 30 min breaks

Agreed order towards a **minimal viable scheduler** (usable on real data; quality rules
come after, the user can fix details by hand meanwhile):
- [x] Refactor: `runs_of_consecutive_blocks` in model.py, used by
      `Schedule.work_stretches_of` and `_short_pieces` in rules.py
- [x] Several days. **Decided: option A**, one block numbering across the weekend:
      block = day number * 96 + (minutes since 06:00) / 15, Friday = day 0. Times before
      06:00 belong to the previous convention day (Saturday 01:00 = block 172). Note
      the naming: "Saturday 01:00" means Saturday's night, which on the calendar is
      Sunday 01:00 (early Sunday morning). The workbook uses the same convention. Rejected
      option B ((day, block) pairs: every rule needs a day loop, misses stretches/breaks
      across 06:00). To do, in this order:
  - [x] model.py: constants `MINUTES_PER_BLOCK = 15`, `BLOCKS_PER_DAY = 96`;
        `Settings.days: tuple[str, ...] = ("Friday", "Saturday", "Sunday")`
  - [x] model.py: helpers `block_of(day, time, settings)`, `time_of(block, settings)`,
        `day_of(block, settings)`, plus constant `DAY_STARTS_AT_HOUR = 6`. All raise
        ValueError with a clear message on bad input (unknown day, time not "HH:MM",
        hour/minutes out of range, not on a 15 min step, block outside the days).
        `time_of` uses `day_of` for its range check. Tests in test_time_blocks.py use
        `@pytest.mark.parametrize` for the invalid inputs (agreed: fine, each case is
        reported as its own test; a for-loop inside one test is not).
  - [x] rules.py: renamed `_blocks_of_day` to `_blocks_of_event`; `// 15` replaced
        with `MINUTES_PER_BLOCK` (refactor, tests stayed green)
  - [x] solver test across a day boundary as a guard:
        `test_work_stretch_across_the_day_boundary_is_at_most_180_minutes` (only Mock
        Mane, Tickets Saturday night 03:00 to Sunday 07:00 = 16 blocks -> NoScheduleFound).
        Possible later: a break across 06:00 (one free block around 06:00 -> raises).
- [x] Availability per day (e.g. a volunteer only there Friday and Sunday). Done in the
      model and solver; turning the workbook's yes/no/range cells into blocks is part of
      reading the workbook (see the decision below and the reader to-dos).
  - **Decided (2026-10-31): positive logic in the workbook.** Volunteers tab, one cell
    per day: `yes` = the whole convention day (06:00-06:00), one time range like
    `08:00-18:00` = only then, `no` or empty = not that day. Case and spaces ignored.
    Anything else is an error naming volunteer, day and value (a typo must never
    silently mean "unavailable"). A volunteer available on no day at all is an error
    ("remove the row if they are not coming"). Range end is exclusive (18:00 = last
    block 17:45); ranges past midnight follow the day convention (Saturday 20:00-02:00);
    end `06:00` means until the end of the convention day (needs a special case:
    `block_of(day, "06:00")` is the *start* of the day). The yes/no/range checks and
    the "never available" error belong in the workbook reader.
  - [x] Model (agreed, field added): `Volunteer.available_blocks: set[int] | None = None`
    (None = no restriction, so existing tests don't change). Not used by the solver yet.
  - **Revised (2026-11-01): no None, the field becomes required** (`set[int]`, no
    default; a default can't know `Settings.days`, and a mutable set isn't allowed as a
    dataclass default anyway). Empty set = never available. "All weekend" is said
    explicitly with `all_blocks(settings)` in model.py.
    - [x] `all_blocks(settings)` with 2 tests in test_time_blocks.py (green)
    - [x] field required, all 37 `Volunteer(...)` calls pass `available_blocks`
      (test_solver_basics.py got a `RULES` with `settings=RULES`; every RULES now also
      passes `days=` explicitly). 55 green, the 5 availability tests still red.
  - [x] Solver: `_create_variables` only makes a variable if `block in
    volunteer.available_blocks` (next to the skill check). 7 tests in
    test_solver_availability.py, all 60 tests green.
  - Test workbook: `tests/data/test_input.xlsx`, same tabs and columns as the draft,
    fictional names only, small demand, availability examples (yes, no, a range, a
    range past midnight, a range ending 06:00).
  - Maybe later: several ranges in one cell (e.g. `08:00-12:00, 14:00-18:00`). Only
    happened once in years; fix by hand for now.
- [x] Read the input workbook (the form CSV is only needed for wishes, so it moves to
      the Event wishes step). Branch `feature/workbook-reader`. All in
      `scheduler/workbook.py`, tests in `tests/workbook/`.
  - **Design (agreed 2026-11-02):** one public reader per tab, each reading only its own
    tab and returning plain data; `read_problem(path: str) -> Problem` opens the file,
    calls them (Settings first: the other readers need the days), builds the `Volunteer`
    objects and does every check that spans tabs. So each reader's tests need only one
    small sheet built in memory with `openpyxl.Workbook()` (helper like
    `_settings_sheet(rows, header)` per test file); only the end-to-end tests open
    `tests/data/test_input.xlsx`. Readers are public (no underscore) because they are
    tested directly; helpers only tested through a reader start with `_`.
    Version 1.0 reads Settings, Volunteers, Posts, Skills, Demand (Events, Wishes and
    Fixed come later). Columns are found by header name, so column order is free and
    extra columns (Team, Notes, ...) are ignored.
  - **Errors:** `WorkbookError(Exception)`, separate from NoScheduleFound (typo in the
    input vs. no schedule possible). Messages start with the tab and name row, volunteer,
    post or value where possible; tests check the important parts with `match=`
    (e.g. `match="Mock Mane.*Saturday.*yse"`). **Stop at the first error for now**
    (collecting all errors: see after version 1.0). Errors from `block_of` and
    `parse_availability` are ValueErrors; the reader catches them and adds the row.
  - Done (177 tests green on 2026-11-02):
    - [x] `cell_text(value) -> str`: strip spaces, empty cell -> "", Excel time value ->
          "HH:MM", numbers -> text. Every cell value goes through it (one place for
          stripping), readers convert to int afterwards.
    - [x] `parse_availability(text, day, settings) -> set[int]`: yes / no / empty / one
          range (end exclusive, past midnight follows the day convention, end 06:00 =
          end of the day, detected by comparing blocks so "6:00" works too); anything
          else, a reversed or empty range, or several ranges is a ValueError.
    - [x] `find_columns(sheet, names) -> dict[str, int]`: header name -> column number
          from row 1; missing or duplicate asked-for header = error naming the tab;
          duplicates of headers not asked for are fine.
    - [x] `read_settings(sheet) -> Settings`: settings by name in the Setting column,
          row order free. Required: Workbook format version (must equal
          `WORKBOOK_FORMAT_VERSION = 1`; raise it only when the workbook layout changes,
          not for every scheduler release), Time step (must be 15), Day boundary (must be
          06:00), Days (comma separated, no duplicates; the single source of the days:
          any names, any number, the first is block 0), Minimum work stretch, Maximum
          work stretch, Minimum break (whole numbers via `_whole_number`). Missing or
          empty, duplicate, or unknown setting = error (catches typos; known-but-unused
          settings such as meals, maximum hours, weights, shift start step and preferred
          maximum are accepted and ignored: `KNOWN_SETTINGS`, `REQUIRED_SETTINGS`).
    - [x] `read_volunteers(sheet, settings) -> dict[str, set[int]]`: Nickname plus one
          availability column per day in `settings.days` (missing = error); days
          combined with `|`. Errors: duplicate nickname, a row with availability but no
          nickname, invalid availability (row, volunteer, day), not available on any day
          ("remove the row if they are not coming"). Completely empty rows skipped.
    - [x] `read_posts(sheet) -> list[Post]`: only the Post column for now (Group and
          Colour are for the output later). Errors: duplicate post, no posts at all. A
          row with only Group/Colour is skipped (a forgotten post name shows up in the
          cross-tab checks).
    - [x] `read_skills(sheet) -> dict[str, dict[str, int]]`: every column except
          Nickname, Team and Notes is a post (via `_post_columns`); score 1/2/3 (number
          or text), empty = never and left out, anything else (also 0) = error naming
          volunteer and post. Errors also: duplicate nickname, scores but no nickname,
          **a volunteer without any score** (user's choice: useless, point it out).
    - [x] `_post_columns(sheet, not_posts) -> dict[str, int]`: shared by Skills and
          Demand (refactored out of `read_skills`); empty headers skipped, duplicate post
          column = error. Its tests live in test_read_skills.py.
    - [x] `read_demand(sheet, settings) -> dict[tuple[str, int], int]`: Day + Time via
          `block_of` (night rows under the previous day), every column except Day, Time
          and Notes is a post. Empty or 0 = closed (left out); a whole number >= 0, else
          error naming row and post. **User's choice:** a row with a Day and Time but no
          number is fine (everything closed; sanity rows before opening / after closing)
          but its Day and Time must still be valid and not a duplicate; only a
          completely empty row is skipped (a day alone as a label is an error). A tab
          without any demand is no error.
    - [x] Workbooks (test workbook and 2026 draft): Settings rows renamed (Minimum/
          Maximum work stretch, Minimum break; "Maximum continuous work" merged into
          Maximum work stretch), Days row and Workbook format version row added. Draft
          backups in ReferenceDocuments (`..._before_settings_rename.xlsx`,
          `..._before_format_version.xlsx`). "Shift start step" and "Preferred maximum
          shift length" keep their names until the soft rules step.
  - [x] `read_problem(path) -> Problem` (done 2026-11-02, test_read_problem.py):
    - [x] the extension first: anything but `.xlsx` = WorkbookError saying to save as
          .xlsx (openpyxl can't read `.ods`, its own error is cryptic). **Decided
          2026-11-02: input stays .xlsx** (the user's Nextcloud uses .ods, but .xlsx keeps
          the tool usable for other volunteer managers).
    - [x] a missing or misspelled tab = WorkbookError naming the tab and listing the
          required ones (instead of openpyxl's KeyError). **User's choice:** only known
          tabs are allowed, like the settings: ReadMe, Events, Wishes and Fixed are known
          but not read yet, any other tab is an error naming it. A file that does not
          exist is a WorkbookError too. Every post on Posts needs a column on Skills
          *and* on Demand (strict, agreed); `read_problem` compares columns with
          `_post_columns`, since the skills/demand dicts leave out empty columns.
          `path` may be `str | Path`. Tested once here, parametrized
          per tab, with a workbook built in memory and saved to pytest's `tmp_path`; not
          in every tab reader (a reader gets a sheet handed to it and only uses
          `sheet.title` in messages).
    - [x] cross-tab checks: every volunteer has a Skills row; every name on Skills is on
          Volunteers; every post column on Skills and every post in Demand is on Posts
          (`Problem.posts` is not used by the solver, so without this a typo in a post
          name silently means "nobody qualified" and a generic NoScheduleFound); every
          post has a Skills column.
    - [x] build `Volunteer(name, skills, available_blocks)` per volunteer and the
          `Problem(volunteers, posts, demand, settings)`.
    - [x] end-to-end tests on `tests/data/test_input.xlsx`: reads without errors, a few
          spot checks, and `solve()` finds a schedule.
- [x] Write output Excel. Branch `feature/output-excel` (the command line goes in the
      same branch). Output is .xlsx.
      **Scope (user, 2026-11-03):** version 1.0 = **post schedules with nicknames**,
      like the old TicketingInfoboothGopher / TicketCheckSecurity tabs. Later updates,
      in this order: a "No double check" tab (for small changes by hand without the
      tool), then an individual schedules tab (see after version 1.0).
      **The old post tabs (2026 schedule .ods, read 2026-11-03):** two header rows
      (row 1 = post or group name merged over its columns, row 2 = slot label "one",
      "two", ... or a sub-post such as "Stairs"); column A = time in half-hour rows,
      a header row per day (FRIDAY, ...), 08:00-02:00 with night rows under the day
      before; one nickname per cell and **a volunteer stays in the same column for
      the whole shift**; grey = closed, white = open; colours with mixed meanings and
      loose text ("General briefing", "Doors Closed") not modelled; posts split over
      two tabs (printable width).
      **Decided (user, 2026-11-03), base version:** no colours at all; 15-minute
      rows; **one tab** with all posts (no split over tabs, printable versions come
      later); rows = day, then time; columns = posts, a post that needs more than one
      person gets numbered columns ("Tickets 1", "Tickets 2", ...); a volunteer stays
      in the same column for their whole shift at that post.
      **Claude's proposal for the details (to confirm):** `scheduler/output.py`,
      `write_schedule(problem, schedule, path) -> None`. Columns A/B = Day and Time
      (like the Demand tab; night rows under the day before); number of columns per
      post = its highest demand, a post that never needs more than one keeps its plain
      name; posts in the order of the Posts tab; rows per day from the first to the
      last block with demand that day (gaps as empty rows, days without demand left
      out). Slots: per post, in time order, someone who worked there in the previous
      block keeps their column, someone new gets the lowest free column (a pure,
      separately tested function). Empty cell = closed (demand is always met
      exactly). Freeze panes under the header and next to Day/Time (**agreed**).
      **Function layout (agreed 2026-11-03, mirrors the input):** `write_output(problem,
      schedule, path)` is the table of contents: new workbook, one
      `create_<name>_sheet(workbook, problem, schedule)` per tab (now only
      `create_schedule_sheet`, name agreed 2026-11-04, matches the tab "Schedule";
      later the check and individual sheets), save. Claude's
      proposal for the pure helpers under `create_schedule_sheet` (to confirm):
      `slot_columns(problem) -> list[tuple[str, int]]` (post, slot number),
      `column_header(post, slot, slot_count) -> str` ("Tickets 2" / "Infobooth"),
      `rows_to_show(problem) -> list[int]`, `assign_slots(schedule) ->
      dict[tuple[str, int, int], str]` ((post, slot, block) -> nickname; only needs
      the schedule; rule: keep your slot if you worked at this post in block - 1,
      otherwise lowest free slot, newcomers in name order; after a break you are a
      newcomer again). The 9 tests in tests/output/test_assign_slots.py are written
      (2026-11-04, user wrote 1-2, Claude the rest; all red, a trial implementation
      in a scratch copy passes them). `assign_slots` implemented, 204 tests green.
      Next: the other helpers (`slot_columns`, `column_header`, `rows_to_show`; tests
      in one file tests/output/test_write_helpers.py, 13 tests approved 2026-11-05,
      a post without any demand gets no columns; a set time window for the rows is
      postponed until after version 1.0, see there). Stubs in output.py and the 13
      tests (15 cases) written by Claude 2026-11-05: all red, a trial implementation
      in a scratch copy makes all 219 green. The user implemented the three helpers;
      plus 4 tests for `column_header`'s ValueErrors (slot count < 1, slot < 1, slot >
      slot count, empty post). 223 tests green (2026-11-05).
      `create_schedule_sheet` (agreed 2026-11-05): times as text ("14:00", from
      `time_of`), the day on every row (easy filtering), a workbook that already has a
      "Schedule" tab = ValueError (user: guards against calling it twice). Stub plus 8
      tests in tests/output/test_create_schedule_sheet.py written by Claude: all red,
      a trial implementation makes all 231 green. Implemented (user wrote steps 1-2,
      Claude 3-5): 231 tests green.
      `write_output(problem, schedule, path: str | Path)` (agreed 2026-11-05): an
      existing file is overwritten (the command line will warn the user); a path not
      ending in .xlsx = ValueError (other file types maybe later). Stub plus 6 tests
      (8 cases) in tests/output/test_write_output.py written by Claude, including an
      end-to-end test (test workbook -> solve -> write; filled cells = total demand):
      all red, a trial implementation makes all 239 green. `write_output` implemented
      by Claude: 239 tests green (2026-11-05). **The output Excel is done**; next: the
      command line (same branch).
      Tab names (agreed): "Schedule" (the post schedule), later e.g. "Individual
      schedules". A file still open in Excel gives a
      PermissionError: turn it into a clear message in the command line, not here.
      Tests mostly on the pure functions, a few write to `tmp_path` and read back.
      Later: post colours, printable versions (split over tabs), "changes vs previous
      run".
- [x] Command line: run it end to end, e.g. `python -m scheduler input.xlsx output.xlsx`
      (until now the solver is only reached from tests).
      **Design (agreed 2026-11-05):** `scheduler/__main__.py` (Python's convention: it
      runs on `python -m scheduler`) with `main(arguments: list[str]) -> int` (exit code
      0 = written, 1 = something went wrong) and `argparse`. Usage: `python -m scheduler
      input.xlsx output.xlsx [--overwrite]`, both names required. Cheap checks first,
      before reading and solving: output must be .xlsx, must not be the input file, its
      folder must exist. Existing output: ask `Overwrite it? [y/N]`, only y/yes goes on
      (Enter = no, then "Nothing written." and exit 1); `--overwrite` skips the question.
      Then read, solve, write, print "Schedule written to ...". Errors = one line on
      stderr, exit 1, no traceback: WorkbookError (its own message), NoScheduleFound
      ("No schedule possible: ..."), PermissionError ("open in Excel? close it").
      Tests in tests/command_line/test_main.py: mostly call `main([...])` directly,
      with pytest's `capsys` (catch printed text) and `monkeypatch` (fake `input()`,
      `solve`, `write_output`); one `subprocess.run([sys.executable, "-m", ...])` test
      runs the real command. Stub plus 14 tests (18 cases) written by Claude: all red,
      a trial implementation makes all 257 green. The user implemented `main` with
      the steps as comments (Claude wrote step 1 and the tidy-ups): 257 tests green,
      and `python -m scheduler tests/data/test_input.xlsx <out>` works (2026-11-05).
      Added (user's idea): an existing output is first opened with `"ab"` and closed
      without writing, so a file locked by Excel is refused *before* solving (Excel
      locks, LibreOffice usually doesn't); the `except PermissionError` in step 4 stays
      for a file opened during solving. Test fakes `open` only in the command line
      module (`monkeypatch.setattr(command_line, "open", ..., raising=False)`). 258 green.
- [x] Clear message when no schedule is possible (done 2026-11-10, see the revised
      roadmap below): simple checks before solving, e.g.
      "Tickets, Saturday 14:00: needs 3, only 2 qualified volunteers available"
      (a bare NoScheduleFound on real data gives no clue where to look).
      **Agreed: expand the error types.** NoScheduleFound becomes the parent class with
      more specific child errors, e.g. `NotEnoughPeople(NoScheduleFound)` (a post/block
      needs more people than are qualified and available), maybe one per kind of
      problem the pre-checks find. Names still to decide. Existing tests keep working:
      `pytest.raises(NoScheduleFound)` also catches the children. New tests can then
      check the specific child (and its message). Plain NoScheduleFound stays for
      "the solver found no schedule" when no pre-check spots a cause.
- [ ] First end-to-end run on real data; compare with the hand-made 2026 schedule.
      **First run done (2026-11-05)** on the 2026 draft: a schedule was found, all 45
      volunteers got work. Claude's analysis (scratch script, totals only): 285 work
      stretches, 155 of them exactly 60 min; 1074 post segments, 830 of them only 15 min
      (stretches of 3-4 segments are typical); 789 post switches inside a stretch, 736
      of them while the old post stayed open with the same or more people (39 because
      it closed, 14 because it needed fewer people). Hours per volunteer 2-20, average
      8.1. Expected: there is no objective yet, so CP-SAT takes any valid schedule.
- [x] **New hard rule (user, 2026-11-05): stay at your post during a work stretch.**
      Switching post inside a stretch only when the old post comes to an end; later a
      soft rule with a weight. On `develop` (one-session step). `add_stay_at_post_rule`
      in rules.py, tests in tests/solver/test_solver_stay_at_post.py.
      **Decided (user):** "comes to an end" = the post needs fewer people at block b than
      at b - 1 (closing = fewer, down to 0), and **only as many people as it needs fewer
      may move to another post at b** (3 -> 2: at most one). **Revised (user):** people
      who stop working at that moment (break, end of availability) use up the drop too:
      movers <= drop - stoppers, checked only when someone moves. Because always
      drop = movers + stoppers - arrivals, this means "when someone moves on from a post,
      nobody new arrives there at that moment"; normal handovers (one stops, another
      starts, same demand) stay allowed. (Rejected: movers + stoppers <= drop, which
      would forbid every handover at an open post.)
      Tests (2026-11-05, written by Claude): 6 tests + 1 skipped stub (test 6: solve the
      test workbook and count afterwards that every move fits the drop). Forced red:
      may_not_leave_an_open_post, only_as_many_as_the_post_needs_fewer, a_volunteer_
      stopping_uses_up_the_switch; guards: closes, needs_fewer_people, after_a_break.
      Trial implementation in a scratch copy: all 264 green (+1 skipped), and the real
      draft is still solvable: 244 of 287 stretches at one post, every move because the
      post closed (38) or needed fewer people (6). But that run took 378 s, the trial
      scanned all of `works` for every volunteer/post/block: build a lookup per
      volunteer/block once (see "Faster model building").
      **Implemented** by Claude in rules.py (per post and moment: drop <= 0 = nobody
      moves on; otherwise count variables for movers/stoppers and
      `movers + stoppers <= drop` only_enforce_if someone moves), one line in
      `solve()`: 264 tests green, test 6 still skipped (2026-11-05).
      **Tightened (user, 2026-11-06), tests changed, rule not yet:** a move is only for
      someone whose stretch would otherwise be shorter than the minimum: a volunteer
      who has worked every one of the last `min_stretch` blocks before b may not move
      on (exactly the minimum done = no move; they stop instead). Avoids e.g. 2.5 hours
      at a closing post plus 15 minutes elsewhere. Planned constraint, per possible move:
      `moves + (their work in each of the min_stretch blocks before b) <= min_stretch`.
      Tests: the moves in tests 1-4 and 7 now happen at block 2 (after 30 min) so each
      still tests one thing; new forced test
      `test_volunteer_who_already_worked_the_minimum_may_not_move_on` (Tickets 0-3,
      then Infobooth 4-7, only Mock Mane): red now. Checked in scratch copies: with the
      planned line all 273 green (+1 skipped); without the stay-at-post rule the 4
      forced tests all find a schedule (so they fail only because of this rule).
      **Implemented** by Claude (2026-11-06): the line is in the `drop > 0` part of
      `add_stay_at_post_rule`, after each `moves` variable. 273 green, 1 skipped.
      **Later (user, 2026-11-05): the output slots with this rule.** If Tickets goes from
      3 to 2 and the volunteer in slot 2 moves on while slot 3 stays, `assign_slots`
      leaves slot 2 empty and slot 3 filled (a gap). The user wants the stayer moved up
      to slot 2 then, but that may cascade back to earlier blocks (the stayer should then
      have been in slot 2 for their whole shift). Think about this and solve it later.
- [x] Faster model building (group variables per volunteer/block once instead of
      `_variables_of` scanning all of `works` on every call), if real data is slow.
      (The solver time limit that was part of this item is now its own item below.)
      Measured (user, 2026-11-06) with `--debug-time` on the 2026 draft** (with
      the tightened stay-at-post rule: a schedule was found). Solving took 5 min 23 s
      (323 s), of which ~311 s is *building the model* and only ~12 s CP-SAT itself:
      | step                          | time      | share |
      |-------------------------------|-----------|-------|
      | add_minimum_stretch_rule      | 3 min 33 s | 66%  |
      | add_minimum_break_rule        | 1 min 1 s | 19%   |
      | add_maximum_stretch_rule      | 22.6 s    | 7%    |
      | add_no_double_booking_rule    | 13.4 s    | 4%    |
      | CP-SAT + reading the schedule | 11.8 s    | 4%    |
      | add_demand_rule               | 0.8 s     |       |
      | add_stay_at_post_rule         | 0.5 s     |       |
      | _create_variables             | 0.1 s     |       |
      Reading the workbook and writing the output: well under a second each.
      Likely cause: the four slow rules call `_variables_of`, which scans all of `works`
      on every call (in add_minimum_stretch_rule several times per volunteer, block and
      run length). add_stay_at_post_rule looks variables up directly with `works.get`
      and takes 0.5 s for similar work, which supports this. Plan to discuss: build a
      lookup {(volunteer, block): [variables]} once (e.g. in solve() or a helper) and
      let `_variables_of` use it; keep the rules' logic the same, so the existing tests
      guard the refactor (they must stay green, and the same schedules must come out).
      Also add_demand_rule scans all of `works` per (post, block): a {(post, block):
      [variables]} lookup. Measure again with `--debug-time` afterwards (only with the
      user's permission for a real-data run).
      **Done by Claude (2026-11-06), refactor without new tests:**
      `_variables_by_volunteer_and_block(works)` in rules.py builds
      `{(volunteer_name, block): [variables]}` once (type alias
      `VariablesByVolunteerAndBlock`); each of the four slow rules makes it once at its
      start as `lookup`, and `_variables_of(lookup, name, first, after)` loops over the
      asked blocks with `lookup.get(...)` instead of scanning works. add_demand_rule
      groups per (post, block) the same way. Rule signatures and solve() unchanged.
      Checked: 284 green, pycodestyle clean, and on the test workbook the model is
      identical (156 variables, 1410 constraints, same order-free fingerprint of the
      linear constraints; scratch script); building the rules went from 0.141 s to
      0.032 s there. **Real draft, measured by the user (2026-11-06): the whole run in
      about 14 s** (was 5 min 23 s for solving alone).

**Roadmap revised (user, 2026-11-08), the rest of version 1.0 in this order:**
- [x] Clear message when no schedule is possible: see the item above (pre-checks,
      NoScheduleFound children). **Done (2026-11-10)** on branch
      `feature/no-schedule-messages` (to merge into `develop`).
      **Design (agreed 2026-11-08; first a small refactor, see below):**
      - Quick, exact checks before CP-SAT starts; if one finds something, a specific
        child of NoScheduleFound is raised; if none does, CP-SAT runs as now and plain
        NoScheduleFound remains for "the rules together don't fit".
      - Check 1, `NotEnoughQualified(NoScheduleFound)`: at a block a post needs more
        people than there are volunteers who are qualified *and* available then. The
        line lists who is qualified and available, and **separately who is qualified
        but not available then** (user), e.g. "Tickets, Saturday 14:00-15:30: needs 3,
        only 2 qualified and available (Mock Mane, Testy Hooves); qualified but not
        available: Dummy Dash". Consecutive blocks with the same problem = one line with
        a time range.
      - Check 2, `NotEnoughVolunteers(NoScheduleFound)`: at a block all posts together
        need more people than there are volunteers available (each post alone may look
        fine), e.g. "Saturday 14:00: the posts need 30 people in total, only 28
        volunteers available".
      - All problems at once (unlike input errors): one error whose message is a list;
        at most 10 lines plus "and N more".
      - Error classes in a new `scheduler/errors.py` (NoScheduleFound and its children;
        WorkbookError maybe too), checks in a new `scheduler/checks.py` with
        `check_problem(problem) -> None`, one line at the start of `solve()`. solver.py
        imports the errors, so `from scheduler.solver import NoScheduleFound` keeps
        working. A separate errors module avoids a circular import (checks needs the
        errors, solver needs checks). The command line already catches NoScheduleFound.
      - **Refactor first (user chose option A, 2026-11-08), on the feature branch, green
        after every step:** 1. `scheduler/errors.py` with WorkbookError and
        NoScheduleFound, workbook.py and solver.py import them from there (test imports
        unchanged); 2. remove hello.py and test_hello.py; 3. test_model.py and
        test_time_blocks.py into `tests/model/`; 4. a one-line-per-module map in
        `scheduler/__init__.py`, layout here updated. Step 1 done by Claude
        (2026-11-08): 284 green, 1 skipped, tests unchanged. Step 2 done (hello.py and
        test_hello.py removed; README project structure brought up to date). Step 3
        done (test_model.py and test_time_blocks.py in tests/model/, 282 green). Step 4
        done (map of the modules in the docstring of scheduler/__init__.py; keep it up
        to date when a module is added, e.g. checks.py). **Option B
        (subpackages
        reading/, solving/, writing/ mirroring the tests) postponed until after the soft
        rules** (user), when rules.py splits into hard and soft rules.
      - Tests in tests/solver/test_checks.py (9 suggested 2026-11-08: raises for a
        post short of qualified people; message names post/day/time; lists qualified+
        available; qualified-but-unavailable don't count (and are listed separately);
        consecutive blocks become one range; all shortages listed; total shortage raises
        NotEnoughVolunteers; both children are NoScheduleFound; a rule conflict still
        gives plain NoScheduleFound).
      - **Stubs written by Claude (2026-11-08), the user implements:** errors.py has
        `NotEnoughQualified` and `NotEnoughVolunteers` (real classes, children of
        NoScheduleFound); `scheduler/checks.py` with `MAX_LINES = 10`,
        `check_problem(problem)` (check 1 first, check 2 only if check 1 found nothing)
        and the helpers `_not_enough_qualified_lines(problem) -> list[str]` and
        `_not_enough_volunteers_lines(problem) -> list[str]` (empty list = fine; private
        since 2026-11-08, user: only used inside checks.py, tested via check_problem), all
        raising NotImplementedError; tests/solver/test_checks.py has the 9 test stubs
        (10 cases: the subclass test is parametrized). `check_problem` is **not yet
        called from solve()**: that line comes once the checks work (otherwise every
        solver test hits NotImplementedError). Map in scheduler/__init__.py updated.
      - **Done (2026-11-10), implemented by the user:** `check_problem` is the first
        line of `solve()` (before building the model). Both helpers describe the shortage
        per block as text (`end_line`, the part after the time) and collect blocks per
        (post, text), so only blocks with exactly the same shortage merge into one time
        range (`runs_of_consecutive_blocks`). `_message(lines)` cuts at `MAX_LINES` and
        adds "and N more"; `_end_time(block_after_last, settings)` gives "06:00" for a
        range that runs to the very end of the convention (where `time_of` would raise).
        Tests added by Claude: different shortages on consecutive blocks give separate
        lines; the message stops at the maximum (monkeypatches `checks.MAX_LINES` to 10)
        and counts the rest; `solve()` raises NotEnoughQualified. 295 green, 1 skipped.
        Measured on large data (user's permission): both checks together ~10 ms, so no
        lookup/cache needed.
      - **Possible further checks (Claude, 2026-11-10; not planned, add when useful):**
        - Maximum hours, **with the maximum-hours item**: total demand in hours > sum of
          everyone's maximum hours; per post, demand in hours > what the qualified
          volunteers can work together (also per day).
        - Groups of posts within one block (between check 1 and check 2): e.g. Tickets
          and Infobooth together need 3 but share the same 2 qualified people. Exact
          version: a matching per block (can every place get its own qualified, available
          volunteer?), catches everything within one block; the hard part is a message
          that names the short group. Only if plain NoScheduleFound on real data leaves
          the user guessing.
        - Rules over time (stretches, breaks; e.g. a post open longer than the maximum
          stretch with one qualified person): hard to check exactly, left to CP-SAT.
        - Later features: a fixed shift that is impossible (not qualified/available),
          meal breaks.
- [x] Maximum hours as a **hard rule** (done 2026-11-12; moved into 1.0, user 2026-11-08; add
      the maximum-hours pre-checks with it, see "Possible further checks" above): per day and in
      total, defaults from the Settings rows "Default maximum hours per day" (8) / "total"
      (16), per volunteer from the Volunteers columns "Max hours per day" / "Max hours
      total" (empty = default). Why: large-data tests gave one volunteer 26 hours while
      16 got nothing, and the PCH draft run went up to 20 hours. (Fair spread stays a
      soft rule after 1.0.)
      **Design (agreed 2026-11-11):** branch `feature/maximum-hours`.
      - Model: `Volunteer.max_minutes_per_day: int | None = None` and
        `max_minutes_total: int | None = None`, in **minutes**; None = no limit (so the
        existing `Volunteer(...)` calls in the tests don't change).
      - Workbook: **whole hours only** (user: the time step may change later, so no
        partial hours; assumption: limits are always at least whole hours). 0 = error
        (not working that day belongs in availability). Settings rows "Default maximum
        hours per day" / "total" become **required** (format version stays 1: every
        workbook already has them). Volunteers columns "Max hours per day" / "Max hours
        total" required headers; **empty cell = the Settings default**, **`none` = no
        limit** for that volunteer (user), anything else = error naming the volunteer.
      - Per day = per convention day (06:00-06:00, night shifts count to their day).
        Only time at a post counts.
      - Order: 1. model fields; 2. rules `add_maximum_hours_per_day_rule` and
        `add_maximum_hours_total_rule` (sum of a volunteer's variables per day / overall
        <= limit in blocks) + tests/solver/test_solver_maximum_hours.py; 3. reader;
        4. pre-checks (see "Possible further checks"); 5. a real-data run (permission!).
      - Done first (2026-11-11), in the template, the test workbook and both real
        workbooks: header row 45 degrees on Volunteers, Posts, Events, Wishes, Fixed;
        Skills and Demand post headers back to vertical (user); fixed background fills
        removed below the header (draft and test workbook; conditional formatting kept).
        Backups `..._before_diagonal_headers.xlsx` and
        `..._before_white_background.xlsx`; cell contents checked identical, 295 green.
      - **Tests written by Claude (2026-11-11; the user had wanted only stubs):**
        test_model.py `test_volunteer_has_no_hour_limits_unless_given`;
        tests/solver/test_solver_maximum_hours.py with 10 tests (daily: beyond raises,
        up to is fine, each day separately, night counts to its convention day; total:
        beyond raises, up to is fine; no limit; own limit per volunteer; together with
        the maximum stretch (user's idea): 8 h Tickets, Mock Mane max 1 h -> raises,
        max 2 h -> found with Mock Mane <= 2 h). Stubs `add_maximum_hours_per_day_rule`
        and `add_maximum_hours_total_rule` in rules.py, not yet called from solve().
        10 red, 1 green (the no-limit test). Trial in a scratch copy: with the rules all
        306 green; without them exactly the 5 forced tests and `..._can_still_be_met`
        fail. **Steps 1-2 done (2026-11-11, user implemented, Claude tidied comments):**
        the two Volunteer fields, both rules (per day via `block_of(day, "06:00")` +
        `BLOCKS_PER_DAY`; total over all days; `if not variables: continue`), two lines
        in solve(). 306 green. **Next: step 3, the reader.**
      - **Step 3 design (agreed 2026-11-11):** one reader per tab stays (user):
        `read_volunteers` returns `dict[str, Volunteer]` (available blocks + both limits,
        `skills={}`; `read_problem` fills in the skills). New Settings fields
        `default_max_minutes_per_day` / `default_max_minutes_total` (default None). Both
        Settings rows required; Settings and Volunteers cells: whole hours >= 1, or
        `none` (case/spaces ignored) = no limit; per day <= 24, total <= 24 * days; per
        day <= total only when both are written as numbers (Settings: the two defaults;
        Volunteers: the same row). Empty Volunteers cell = the Settings default.
        Shared helper `_hour_limit(text, max_hours) -> int | None` (stub, ValueError;
        tested via the readers). Stubs written by Claude: 8 tests (13 cases) in
        test_read_settings.py, 10 tests (16 cases) in test_read_volunteers.py (section
        comments "Availability" / "Hour limits"), 1 in test_read_problem.py (needs
        Testy Hooves with 4 per day / none total in tests/data/test_input.xlsx).
        306 green, 30 skipped. The existing read_volunteers tests are left as they are
        on purpose: the user wants to see them fail after the refactor, then fix them.
        **Order (user):** 3a Settings first (fill in the 8 settings tests, implement,
        green), then 3b read_volunteers + read_problem (refactor, fix old tests, the
        10 + 1 new tests).
        **3a done (2026-11-11):** user wrote the settings tests (the separate "missing"
        test merged into `test_missing_setting_raises_workbook_error`; GOOD_ROWS 6/12;
        `_rows_with`/`_rows_without` take optional base rows); Claude implemented
        `_hour_limit(text, max_hours)` (ValueError, "none" -> None, int(), 1..max,
        hours * 60) and the part in `read_settings` (WorkbookError with the setting in
        front; per day <= total only when both numbers). Settings fields default None.
        test_read_problem's in-memory workbook got the two rows (8/16). 319 green,
        17 skipped; both real workbooks still read. **Next: 3b.**
        **Then (agreed 2026-11-11, after 3b): refactor the readers**, tests stay as they
        are: `read_settings` becomes a table of contents with `_settings_by_name(sheet)`,
        `_check_fixed_settings(...)`, `_days(text)`; `read_volunteers` gets
        `_available_blocks_of_row(...)`; and one shared helper
        `_hour_limits(per_day: (name, text), total: (name, text), number_of_days) ->
        (int | None, int | None)` (ValueError naming the setting/column, per day <= total
        only when both are numbers, empty -> None so read_volunteers fills in the
        default); the readers only put "Settings, " / "Volunteers, row N (nickname), " in
        front. Order reversed by the user (they were halfway through read_volunteers).
        **3b, code done (2026-11-11; user implemented, Claude fixed):** read_volunteers
        returns `dict[str, Volunteer]` (skills={}), empty limit cell = the settings
        default, errors "Volunteers, row N (nickname), Max hours per day: ...", per day
        <= total only when both cells are written, a row with only limits but no nickname
        is an error; read_problem fills in `volunteer.skills`. Old tests adapted (HEADER
        with the two columns, compare `.available_blocks`; test_read_problem's in-memory
        workbook + GOOD_PROBLEM 480/960). 319 green, 17 skipped (the 10 + 1 new stubs).
        **Next:** the user fills in the 10 Volunteers stubs + test 19, then the refactor.
        **Refactor part 1 done (2026-11-11, Claude):** `_hour_limits` in workbook.py,
        used by both readers (messages now "Settings, <setting>: ..." and "Volunteers, row
        N (nickname), <column>: ..."); read_settings step 4 also rejects an empty required
        setting (else an empty default limit would silently mean "no limit"). 319 green,
        17 skipped. Still to do: `_settings_by_name`, `_check_fixed_settings`, `_days`,
        `_available_blocks_of_row`. Then `_hour_limit(name, text, max_hours)` names the
        setting/column itself (no re-raise in `_hour_limits`, user's choice).
        **Tests filled in by Claude (2026-11-11, on request):** the 10 Volunteers tests
        (RULES defaults 360/720) and test 19 (test workbook: Testy Hooves 4 per day / none
        total). 336 green, nothing skipped. Code came first, so each was checked by hand
        in a scratch copy: break one line, the matching test goes red.
        **Reader refactor done (2026-11-11, Claude, tests unchanged, 336 green):**
        read_settings is a table of contents over `_settings_by_name`,
        `_check_setting_names`, `_check_fixed_settings`, `_days` and `_hour_limits`;
        read_volunteers uses `_available_blocks_of_row` and `_hour_limits_of_row`. Helpers
        used by one reader sit right after it.
      - **Step 4 design (agreed 2026-11-11):** one `NotEnoughHours(NoScheduleFound)`
        (the message says which kind). In checks.py `_not_enough_hours_at_post_lines` (per
        post: a line per short day, plus one for the whole convention) and
        `_not_enough_hours_in_total_lines` (all posts together, same), run after checks 1
        and 2 and per post before in total. What a volunteer can work: on a day the
        lowest of their available hours that day, limit per day and limit total; over the
        convention the lowest of limit total and the sum of their days (None drops out).
        Stubs written by Claude: the error class, both helpers (NotImplementedError, not
        yet called from check_problem), 12 test stubs in test_checks.py ("Hours"
        section); the subclass test is now `test_every_check_error_is_a_kind_of_...` with
        NotEnoughHours added. 337 green, 12 skipped. The user starts with tests 1, 2, 5, 6.
        **Message lines (user):** "{post}, {day}: ..." for one day and "{post}, over all
        days: ..." for the whole convention (the rest of the line, e.g. "needs 4 hours, the
        qualified volunteers can work 2 hours (Mock Mane)", still to settle in test 11).
        Test 1 written by the user (2 hours on Friday + 2 on Saturday, Mock Mane max 2 h
        total: only "over all days" is short). All posts together: "All posts, {day}: ..."
        and "All posts, over all days: ...". **Tests 1-4 by the user, 5-12 filled in by
        Claude (2026-11-12, on request):** 7 red ("raises" and message tests), the guards
        green. Trial implementation in a scratch copy: all 349 green with the checks
        called; tests 9 and 10 each fail without their cap (availability / total per day).
        **Step 4 done (2026-11-12):** both checks implemented by the user, called from
        `check_problem` after checks 1 and 2 (committed `28c8a19`). Then merged by Claude
        (tests unchanged, 349 green): both functions are short wrappers around
        `_hours_lines(problem, label, posts, volunteers, who, show_names)` ("All posts" =
        every post with demand, every volunteer, no names), helpers `_hours_line`,
        `_minutes_can_work_on_day`, `_hours_text`. **Step 5:** PCH 2026 draft run
        (2026-11-12, user's go): schedule found, 44.8 s (CP-SAT ~41 s; times in
        RUN_TIMES.md). With a limit for every volunteer (defaults 8/16) CP-SAT took
        37-62 s; with the defaults `none` ~12 s, steady. **Decided (user, 2026-11-12):
        default hour limits are `none`** in the template, the PCH draft and the UKPC
        workbook; the template's Meaning warns that a number there is very costly; limits
        only for the few volunteers who need one. (The test workbook keeps 8/16: test 19
        relies on them.) **Next:** the UKPC timing run, then merge the branch into
        `develop`. Possible later: skip a limit that can never be reached (the volunteer
        can't work that many blocks anyway), only useful if someone sets numbers again.
        **Status at the end of the morning of 2026-11-11 (continue here):** 3b committed
        (`cf0bfdf`, the accidentally committed template was taken out with an amend).
        The user chose to do **the reader refactor next** (the plan above:
        `_hour_limits` shared by read_settings and read_volunteers, split read_settings
        into `_settings_by_name` / `_check_fixed_settings` / `_days`, and
        `_available_blocks_of_row` for read_volunteers), with the tests unchanged and
        green; then the 10 Volunteers stubs + test 19 (Testy Hooves 4 per day / none in
        the test workbook), then the pre-checks for maximum hours.
- [x] Warnings before solving (user, 2026-11-11; in 1.0, right after maximum hours):
      problems that don't stop a run but are probably a mistake in the input. First one:
      a volunteer who can never be scheduled (no block where a post they're qualified
      for is open while they're available = no variables), e.g. "Mock Mane can never be
      scheduled: no post they are qualified for is open while they are available".
      Proposed design: `find_warnings(problem) -> list[str]` in checks.py (plain list,
      not Python's `warnings` module, not an exception); the command line calls it before
      solving and prints each line with "Warning: " in front, then carries on; solve()
      stays silent. Possible later warnings with the same mechanism: a post that is
      never open, a volunteer available for less than the minimum stretch, after the
      run who got no shift at all (see the CLI summary idea).
      **Agreed (user, 2026-11-12), on `develop`:** design as proposed, but the warnings go
      to **stdout** via `_say` ("[14:03:12] Warning: ..."; every stdout line starts with
      the time, see test_progress_messages_start_with_the_time), printed after reading and
      before solving. "Can never be scheduled" = no (post, block) in the demand with a
      post they are qualified for and a block where they are available (= no solver
      variables). **Stubs written by Claude:** `find_warnings` in checks.py
      (NotImplementedError), 6 test stubs in tests/solver/test_warnings.py, 2 in
      test_main.py (section "warnings before solving"; they will monkeypatch
      `command_line.find_warnings`, so `__main__.py` imports it by name). 349 green,
      8 skipped. Tests filled in by Claude (on request; the user's first drafts fixed),
      checked against a trial. **Done (2026-11-12), implemented by Claude:**
      `find_warnings` + helper `_can_ever_be_scheduled(volunteer, problem)` in checks.py;
      `main` prints each line with `_say(f"Warning: {line}")` right after reading. 357
      green. The test workbook gives no warnings.
- [ ] Solver time limit (a setting), so a big run can't hang forever (large-data runs
      with minimum stretch 60 / break 30 took over 3 minutes in CP-SAT).
- [ ] Compare a real PCH 2026 run with the hand-made 2026 schedule (see "First
      end-to-end run" above; the run works, the comparison isn't done).
- [x] Small: test 6 of the stay-at-post rule. **Dropped (user, 2026-11-11), stub removed:**
      the solved test workbook has no post switches at all (checked: 0 moves in 3 runs),
      so the test would check nothing; the 7 small solver tests already cover the rule.
      295 green, nothing skipped.
- [ ] Small: a damaged file with an .xlsx name (zipfile.BadZipFile) becomes a clear
      WorkbookError.
- [ ] Small: optional guard test for a break across 06:00 (hello.py and test_hello.py
      were removed on 2026-11-08)

**Version 1.0 = all of the above**: a schedule for real data that follows the hard rules
(except meal breaks and fixed shifts; including maximum hours), run from the command
line. The user fixes details by hand.

After the minimal viable scheduler:
- [ ] Fixed shifts placed by hand are kept (Fixed tab). **Postponed (2026-11-01):**
      decide after the first real run. Mainly useful for re-runs after changes (pin what
      is already agreed, refill only the gap) and for shifts arranged in advance. The user
      has so far only changed shifts by hand. Small to add later: one rule pinning
      variables to 1, a clear error if a fixed shift is impossible (not qualified / not
      available), and `Problem.fixed` with an empty default (doesn't depend on settings,
      so no test churn). The reader skips the Fixed tab until then.
- [ ] Output: a "No double check" tab (like the old one: events, wishes, one column
      per volunteer grouped by team) for small changes by hand without the tool.
- [ ] Possible feature (not for 1.0, agreed 2026-11-11): `check_schedule(problem,
      schedule)` re-checks every hard rule on a finished schedule in plain Python (no
      CP-SAT) and lists the violations. Upsides: an independent second implementation
      catches bugs in the rules themselves (CP-SAT follows the rules as written, not as
      meant); checks all combinations on real runs, not only the tested ones; and checks
      schedules that did not come from solve(): hand corrections after a run (the
      automatic version of "No double check"), old hand-made schedules (e.g. 2026), later
      fixed shifts. Cost: every rule written twice; checking hand edits needs a reader
      for the output workbook.
- [ ] Output: an individual schedules tab (per volunteer their shifts; the old
      "Individual Schedules" tab is from the 2025 layout and does not match 2026).
      **Use the post colours** from the Colour column on Posts (user, 2026-11-11; the
      reader then also reads Group and Colour). Showing the colour on the Posts tab
      itself was considered and skipped for now (options: fixed fills, or conditional
      formatting with a fixed palette of group colours).
- [ ] Output: a set time window for the Schedule rows (agreed 2026-11-05, postponed by
      the user; version 1.0 fits the rows to the demand). Optional Settings row, e.g.
      `Schedule shows` = `08:00-02:00`, same format and rules as an availability range
      (reuse the `parse_availability` parsing); `Settings.schedule_shows: str = ""`
      (empty = fit to demand), read by `rows_to_show(problem)` (signature unchanged).
      Optional row, so the workbook format version stays 1. **User's choices:** the
      window is a minimum (demand outside it still gets rows, never hide a shift); a day
      without demand is left out entirely; one window for every day. Tests planned for
      test_write_helpers.py: set window shows rows before and after the demand
      (08:00-20:00, demand 10:00-12:00); window past midnight belongs to the same day
      (Saturday 08:00-02:00 ends at block 175); demand outside the window still gets
      rows; day without demand gets no rows even with a window. Plus in
      test_read_settings.py: accepted and stored, missing row gives "", invalid range =
      WorkbookError naming the setting.
- [ ] Nicer command line (user's wish list, 2026-11-05):
  - Timer: `time.perf_counter()`, e.g. "Solved in 12.3 s"; better per phase (reading,
    building the model, solving, writing) to see where the time goes. Small, could be
    done any time (also helps judge "faster model building").
    **Partly done (2026-11-05):** `_say(message)` in `__main__.py` prints each step to
    stdout with the time and `flush=True`: "[14:03:12] Reading ...", "Solving (this can
    take a few minutes)", "Writing ...", "Schedule written to ...". Two tests in
    test_main.py (steps in order; every line starts with [HH:MM:SS]). 266 green.
    Then "Solved, this took 5 min 12 s" right after solving (`time.perf_counter()`
    around `solve()`; public `format_duration(seconds)`: under 60 s "3.2 s", else whole
    minutes and seconds, rounded first so 119.6 = "2 min 0 s"). 272 green.
    Building the model and solving are still one step (both inside `solve()`).
  - **`--debug-time` (user, 2026-11-06), in progress:** `scheduler/helpers.py` with an
    on/off switch `debug_time_on = False`, `set_debug_time(on: bool)` and
    `debug_print(message: str, destination: TextIO | None = None) -> None`: only when on,
    prints "DEBUG [14:03:12.345] message" (milliseconds) with flush=True to destination,
    default sys.stdout looked up at call time (a `=sys.stdout` default would be fixed
    when Python reads the def, so capsys could not catch it). Separate module because
    rules.py and solver.py will call it too; the command line will call
    `set_debug_time(options.debug_time)`. 7 tests in tests/test_helpers.py (tests that
    switch it on use monkeypatch, so the switch is reset after each test). Stubs plus
    tests written by Claude: 6 red, 1 guard green; a trial implementation makes all 280
    green. Implemented by the user (2026-11-06; first with a tab before the time, then
    changed to a "DEBUG " prefix, user's choice). pycodestyle added to requirements.txt and
    the whole project made clean (`--max-line-length=100`).
    The flag: 2 tests in test_main.py ("debug output" section): `--debug-time` switches
    `helpers.debug_time_on` on; without the flag `main` switches it off, even if it
    was on. Both red (argparse: unrecognized argument; switch untouched); a trial
    (`add_argument("--debug-time", action="store_true")`, then
    `set_debug_time(options.debug_time)` right after `parse_args`) makes all 282
    green. Implemented by Claude (2026-11-06): 282 green, shown in `--help`.
    **debug_print calls (user's idea, 2026-11-06):** not in the table-of-contents
    functions (read_problem, solve, write_output) but as the first line of each
    `read_*` tab reader ("read_settings: reading tab Settings"), each `add_*_rule`
    ("add_demand_rule: adding the rule") and each `create_*_sheet` ("creating tab
    Schedule"). So a new reader/rule/tab announces itself, and the time between two
    lines is how long the step before took. Test:
    `test_debug_time_flag_prints_debug_lines_from_reading_solving_and_writing`
    (one line from each part). 283 green. Plus, in solver.py, a line at the start of
    `_create_variables` and one just before `solver.solve(model)` in
    `_solve_and_read_schedule` ("running CP-SAT"), so building the model and CP-SAT's
    own search can be told apart; test
    `test_debug_time_flag_prints_debug_lines_for_the_variables_and_cp_sat`. 284 green.
  - Progress: with only hard rules CP-SAT stops at the first valid schedule, so no
    percentage is possible; show the phase plus elapsed time, and CP-SAT's own log
    (`log_search_progress = True`) behind `--verbose`. Once there are soft rules, a
    `CpSolverSolutionCallback` can report each better schedule (penalty and the gap to
    CP-SAT's best bound), and a time limit means "keep the best so far".
  - Ideas (Claude, not decided): a summary after a run (volunteers, posts, shifts,
    hours per volunteer min/max/average, who got no shift); `--check` (only read and
    check the workbook, no solving); `--time-limit SECONDS` (goes with the time-limit
    setting); `--open` (open the output when done, `os.startfile`); optional output
    name (e.g. `<input>_schedule.xlsx`, maybe with a timestamp); `--seed` (same schedule
    again, or an alternative); `--verbose` / `--quiet`; `--version` (scheduler and
    workbook format version); a separate exit code for "no schedule possible" (e.g. 3).
- [ ] Collect and show all input errors at once instead of stopping at the first one
      (e.g. a list of every typo in the workbook; fits the window program later).
- [ ] Time step and day boundary configurable (e.g. 30 min blocks, another boundary).
      Not only the reader: `MINUTES_PER_BLOCK`, `BLOCKS_PER_DAY` and `DAY_STARTS_AT_HOUR`
      move from model.py constants into `Settings`, used by `block_of`/`time_of`/rules.
      Raise the workbook format version if the Settings rows change.
- [ ] Maybe: also read `.ods` (Nextcloud / LibreOffice). openpyxl can't; options: a
      second front-end with e.g. `odfpy` giving the same cell values (the tab readers
      stay the same), or converting with LibreOffice (`soffice --headless --convert-to
      xlsx`, needs LibreOffice installed).
- [ ] Soft rules (first objective): start/end on :00/:30, stay at one post, avoid short
      stretches, prefer higher skill scores, prefer work stretches of at most 120 min
- [ ] Meal breaks. Check the windows with the user first: the workbook Settings say
      lunch 11:30-14:00 and dinner 17:30-19:30, this file says 12:00-14:00 and
      18:00-19:00.
- [ ] Event wishes (includes reading the form CSV). Then also revisit the Events tab
      columns: the template still has the header "Name in 2026 sheet" (user, 2026-11-08:
      change it when this functionality is added).
- [ ] Fair spread of hours (soft rule; maximum hours moved into version 1.0)
- [ ] Output: with the stay-at-post rule, a gap can appear between slot columns when a
      post needs fewer people (see the stay-at-post item; cosmetic, the right people are
      in the schedule).
- [ ] Maybe: Question vetting, Manestage clean and Sardine duty by the same person
- [ ] **Think about one-off event shifts (user, 2026-11-08; Claude: remind the user once
      the large-data test runs are done).** Reminded 2026-11-12; user: discuss it right
      after the 1.0 release. Big conventions have many "posts" that are
      really a single event (open once, for one hour, one person). As separate posts they
      make the Posts/Skills/Demand tabs very wide. Ideas to discuss: an "Event assistance"
      post with the event name as a note, posts with a group and a shared skill, or a
      separate tab for one-off tasks.
- [ ] Maybe: switch rules on/off from the workbook (may need a Rule class then)
- [ ] Future wish: a small program with a window, e.g. to pick the input workbook, start
      a run and show errors clearly, so it can be used without the command line.
      Technology still to choose (e.g. tkinter for a real window, Streamlit for a page in
      the browser).

Current position: Steps 1 and 2 are done. Hard rules in rules.py: demand, no double
booking, maximum stretch (sliding window), minimum break (forbid "work, short gap,
work"), minimum stretch (forbid "free, short run, free", with an escape variable per
matching short piece of demand). Helpers: `_blocks_of_event`, `_variables_of`,
`_short_pieces` in rules.py; `runs_of_consecutive_blocks` in model.py (shared, tested).
**Several days (option A) is done**: constants, `Settings.days`, the time helpers
`block_of`, `time_of`, `day_of` (in model.py, tested in test_time_blocks.py), the
rules.py rename to `_blocks_of_event`, and a cross-day guard test.
2026-10-31/11-01: roadmap revised (version 1.0 defined, README Status synced),
availability decided (positive logic, see the roadmap item), test workbook
`tests/data/test_input.xlsx` made, the 2026 draft converted to yes/no (backup kept in
ReferenceDocuments). **Availability per day is done** in model and solver:
`Volunteer.available_blocks` is required (no None), `all_blocks(settings)` for "all
weekend", every test RULES passes `days=` explicitly, `Works` type alias, type hints
agreed for all new functions. 60 tests green.
Fixed shifts postponed to after version 1.0.
**Reading the input workbook is done** (2026-11-02, branch `feature/workbook-reader`):
`read_problem(path)` checks the file and tabs, calls the five tab readers, checks
across tabs and builds the Problem. 195 tests green; the test workbook goes all the
way to a schedule, and the real 2026 draft reads without errors (not solved yet).
Merged into `develop` (fast-forward) and the feature branch deleted, local and remote
(2026-11-02). **Next (user's choice, 2026-11-02): the output Excel and the command
line first**, then the clear message when no schedule is possible (still part of
version 1.0, roadmap order changed accordingly), then the first real run.
2026-11-03: on branch `feature/output-excel`; old schedule read, scope agreed (post
schedules first), design proposal and open questions under the output Excel item.
2026-11-05: **output Excel and command line done** on `feature/output-excel`
(`write_output` + `create_schedule_sheet` + helpers in output.py, `main` in
`scheduler/__main__.py`), 257 tests green. Next: merge the branch into `develop`, then
the clear message when no schedule is possible, then the first real run (save the
output outside the repo: it holds real nicknames).
Possible small follow-up: a file with an .xlsx name that is not a real workbook
(e.g. damaged) gives openpyxl's own error (zipfile.BadZipFile), not a WorkbookError.
In this session the user often asked Claude to write the tests and/or the code once
they had approved the test list; Claude then also checked the tests against a trial
implementation in a scratch copy (and against both workbooks) before handing over.
Claude reviews and explains; only changes code when asked.

## Step 2 plan: work stretches and breaks (done; kept for reference)

Note: the solver tests below were later renamed to say "the minimum/maximum" instead of
a number (e.g. `test_work_stretch_longer_than_the_maximum_raises_no_schedule_found`) and
now pass `settings=RULES` explicitly.

Blocks: 1 block = 15 min, 4 = 60 min, 12 = 180 min.

Helper `Schedule.work_stretches_of(volunteer) -> list[(first_block, block_after_last)]`,
regardless of post. Pure Python tests (red first):
a. test_consecutive_blocks_form_one_work_stretch (Tickets 0-3 -> [(0, 4)])
b. test_a_gap_splits_work_into_two_stretches (0-3, 6-9 -> [(0, 4), (6, 10)])
c. test_switching_post_continues_the_same_stretch (Tickets 0-3, Infobooth 4-7 -> [(0, 8)])
d. test_volunteer_without_assignments_has_no_stretches (-> [])

Solver tests (forced = only one outcome obeys the rules, so reliably red first):
1. test_work_stretch_longer_than_180_minutes_raises_no_schedule_found
   (only Mock Mane, Tickets 0-15) forced
2. test_continuous_work_across_two_posts_is_at_most_180_minutes
   (only Mock Mane, Tickets 0-7 then Infobooth 8-15) forced, raises
3. test_break_of_15_minutes_raises_no_schedule_found
   (only Mock Mane, Tickets 0-7, gap 1 block, Tickets 9-16) forced
4. test_break_of_30_minutes_is_allowed
   (only Mock Mane, Tickets 0-7, gap 2 blocks, Tickets 10-17) guard, succeeds
5. test_extra_person_needed_for_30_minutes_may_work_just_those_30_minutes
   (Mock Mane + Testy Hooves, Tickets needs 2 in blocks 0-1, 1 in blocks 2-7) succeeds
6. test_two_posts_together_can_make_up_the_60_minutes
   (as 5, plus Infobooth 2-3 that only Testy Hooves can do) guard, succeeds
7. test_post_open_less_than_60_minutes_can_be_worked
   (only Mock Mane, Tickets 0-1) guard for the short-piece exception
8. test_work_stretch_shorter_than_minimum_raises_no_schedule_found
   (Settings min 150, max 180; Mock Mane + Testy Hooves; Tickets needs 1 in 0-15:
   any split leaves a piece under 150 min) forced. With min 60 no tiny forced
   scenario was found, hence the setting.
9. test_minimum_stretch_can_be_changed_in_the_settings
   (scenario impossible with min 60 but fine with min 30; still to design)
10. test_long_opening_is_split_into_stretches_of_allowed_length
   (Tickets 0-15, Mock Mane + Testy Hooves: every stretch 4-12 blocks) property,
   needs the helper, so written after it
