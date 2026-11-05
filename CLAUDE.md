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
   Do not commit, push, branch or run other git commands that change state. Suggest a
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

## Privacy (important)

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
  Python: a function only has to exist when it is called.)
- **pytest** for tests. Version 1.0 runs from the command line; later a small program
  with a window (see the roadmap).

## Repository layout

```
ReferenceDocuments/   (not in git) real data, DATA_NOTES.md, draft input workbook
scheduler/            model.py (data classes), solver.py, rules.py (hard rules),
                      workbook.py (reads the input workbook), output.py (writes the
                      output workbook), hello.py (setup check)
tests/                test_hello.py, test_model.py, test_time_blocks.py;
                      data/test_input.xlsx (made-up workbook)
tests/solver/         test_solver_availability.py, test_solver_basics.py,
                      test_solver_work_stretches.py
tests/output/         test_assign_slots.py, test_write_helpers.py,
                      test_create_schedule_sheet.py, test_write_output.py (tests of
                      writing the output workbook)
tests/workbook/       test_celltext.py, test_availability.py, test_find_columns.py,
                      test_read_settings.py, test_read_volunteers.py,
                      test_read_posts.py, test_read_skills.py, test_read_demand.py,
                      test_read_problem.py (one test file per reader part)
                      Every test folder has an empty __init__.py (like tests/ itself).
requirements.txt      ortools>=9.15, openpyxl>=3.1, pytest>=8.0
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
The workbook has its own ReadMe tab explaining each tab. Yellow cells = a guess or
question to check. Posts include e.g. Tickets, Infobooth, Vendorguarding,
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
- [ ] Write output Excel. Branch `feature/output-excel` (the command line goes in the
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
      all red, a trial implementation makes all 239 green. Next: implement
      `write_output`, then the command line (same branch).
      Tab names (agreed): "Schedule" (the post schedule), later e.g. "Individual
      schedules". A file still open in Excel gives a
      PermissionError: turn it into a clear message in the command line, not here.
      Tests mostly on the pure functions, a few write to `tmp_path` and read back.
      Later: post colours, printable versions (split over tabs), "changes vs previous
      run".
- [ ] Command line: run it end to end, e.g. `python -m scheduler input.xlsx output.xlsx`
      (until now the solver is only reached from tests)
- [ ] Clear message when no schedule is possible: simple checks before solving, e.g.
      "Tickets, Saturday 14:00: needs 3, only 2 qualified volunteers available"
      (a bare NoScheduleFound on real data gives no clue where to look).
      **Agreed: expand the error types.** NoScheduleFound becomes the parent class with
      more specific child errors, e.g. `NotEnoughPeople(NoScheduleFound)` (a post/block
      needs more people than are qualified and available), maybe one per kind of
      problem the pre-checks find. Names still to decide. Existing tests keep working:
      `pytest.raises(NoScheduleFound)` also catches the children. New tests can then
      check the specific child (and its message). Plain NoScheduleFound stays for
      "the solver found no schedule" when no pre-check spots a cause.
- [ ] First end-to-end run on real data; compare with the hand-made 2026 schedule
- [ ] Faster model building (group variables per volunteer/block once instead of
      `_variables_of` scanning all of `works` on every call), if real data is slow.
      Plus a solver time limit (a setting), so a big run can't hang forever.
- [ ] Small: optional guard test for a break across 06:00; remove hello.py and
      test_hello.py once they're no longer useful

**Version 1.0 = all of the above**: a schedule for real data that follows the hard rules
(except meal breaks and fixed shifts), run from the command line. The user fixes details by hand.

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
- [ ] Output: an individual schedules tab (per volunteer their shifts; the old
      "Individual Schedules" tab is from the 2025 layout and does not match 2026).
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
- [ ] Event wishes (includes reading the form CSV)
- [ ] Maximum hours and fair spread
- [ ] Maybe: Question vetting, Manestage clean and Sardine duty by the same person
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
