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
   **Code in `scheduler/` and `tests/`: only suggest it, the user types it in.** Then
   review their file when asked.
2. **Test-driven development.** For every step:
   tests first and let the user read them, run them and see them fail (red),
   then just enough code to pass (green), tidy up, the user commits.
3. **Every test uses `# Arrange`, `# Act`, `# Assert` comments**, even when a section
   is empty (write a short comment saying why). Keep Act and Assert on separate lines
   (`result = f()` then `assert result == ...`). One behaviour per test, a name that
   reads like a sentence, a one-line docstring.
4. **The user handles version control** in VS Code / Sourcetree, on the `develop` branch.
   Do not commit, push, branch or run other git commands that change state. Suggest a
   commit message when a step is done. Read-only git commands (status, log, branch) are fine.
5. **Python only.** Python **3.14** in `.venv` (OR-Tools has no 3.15 wheels yet).
   Use the newer lowercase OR-Tools API (`new_int_var`, `add`, `solve`, `value`).
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
- **Shared helpers:** `_variables_of` in rules.py collects a volunteer's variables in a
  block range (used by every per-volunteer rule). `runs_of_consecutive_blocks` in
  model.py (public, tested in test_model.py) is used by `Schedule.work_stretches_of`
  and `_short_pieces`.
- **openpyxl** for reading/writing `.xlsx`. No pandas for now.
- **pytest** for tests. Later possibly **Streamlit** as a simple UI.

## Repository layout

```
ReferenceDocuments/   (not in git) real data, DATA_NOTES.md, draft input workbook
scheduler/            model.py (data classes), solver.py, rules.py (hard rules),
                      hello.py (setup check)
tests/                test_hello.py, test_model.py, test_solver_basics.py,
                      test_solver_work_stretches.py, test_time_blocks.py
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

Tabs: ReadMe, Settings, Meals, Volunteers, Posts, Skills, Events, Demand, Wishes, Fixed.
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
- [ ] Several days. **Decided: option A**, one block numbering across the weekend:
      block = day number * 96 + (minutes since 06:00) / 15, Friday = day 0. Times before
      06:00 belong to the previous convention day (Saturday 01:00 = block 172). Note
      the naming: "Saturday 01:00" means Saturday's night, which on the calendar is
      Sunday 01:00 (early Sunday morning). The workbook uses the same convention. Rejected
      option B ((day, block) pairs: every rule needs a day loop, misses stretches/breaks
      across 06:00). To do, in this order:
  - [x] model.py: constants `MINUTES_PER_BLOCK = 15`, `BLOCKS_PER_DAY = 96`;
        `Settings.days: tuple[str, ...] = ("Friday", "Saturday", "Sunday")`
  - [ ] model.py: helpers `block_of(day, time, settings)`, `time_of(block, settings)`,
        `day_of(block, settings)`. Stubs are in model.py; 10 tests written in
        tests/test_time_blocks.py (8 red, 2 green by coincidence because the block_of
        stub returns 0). Next: the user implements the three helpers (hint given:
        `"13:30".split(":")`, minutes since 06:00, add 24 h for times before 06:00;
        unknown day or a time not on a 15 min step -> ValueError with a clear message).
  - [ ] rules.py: rename `_blocks_of_day` to e.g. `_blocks_of_event`; replace `// 15`
        with `MINUTES_PER_BLOCK` (refactor, tests stay green)
  - [ ] one or two solver tests across a day boundary as guards (e.g. only Mock Mane,
        Tickets Saturday night 03:00 to Sunday 06:45 = 16 blocks -> NoScheduleFound)
- [ ] Availability per day (e.g. a volunteer only there Friday and Sunday)
- [ ] Read input workbook and form CSV. To do:
  - [ ] validate names. `Problem.posts` is not used by the solver yet, so a typo in a
        post name (in demand or skills) silently means "nobody qualified" and gives a
        generic NoScheduleFound. Check every post name against `posts` and raise a
        clear error naming the typo.
  - [ ] the draft workbook already fits option A: Demand/Events/Fixed use Day + Time
        columns, Saturday night rows (00:00-02:45) are listed under "Saturday", and
        Volunteers has Friday/Saturday/Sunday availability columns. Convert with
        `block_of` while reading.
  - [ ] align Settings names with the code: the workbook has "Minimum/Maximum shift
        length" and "Maximum continuous work" (one concept in the code: work stretch);
        rename to e.g. "Minimum/Maximum work stretch". "Shift start step" is now a soft
        rule.
  - [ ] list of days: add a "Days" row to the Settings tab (most explicit).
  - [ ] the code assumes time step 15 min and day boundary 06:00: check that the
        workbook's Settings say the same, clear error if not.
  - [ ] meal windows differ: workbook Settings say lunch 11:30-14:00 and dinner
        17:30-19:30, this file says 12:00-14:00 and 18:00-19:00. Check with the user
        at the meal breaks step.
- [ ] Write output Excel (overview, per post, per volunteer; show changes vs previous
      run). Use `time_of`; show night rows under the previous day (as the workbook does).
- [ ] First end-to-end run on real data; compare with the hand-made 2026 schedule
- [ ] Faster model building (group variables per volunteer/block once instead of
      `_variables_of` scanning all of `works` on every call), if real data is slow

After the minimal viable scheduler:
- [ ] Soft rules: start/end on :00/:30, stay at one post, avoid short stretches
      (first objective)
- [ ] Meal breaks
- [ ] Event wishes
- [ ] Maximum hours and fair spread
- [ ] Maybe: switch rules on/off from the workbook (may need a Rule class then)
- [ ] Maybe: Streamlit UI

Current position: Steps 1 and 2 are done. Hard rules in rules.py: demand, no double
booking, maximum stretch (sliding window), minimum break (forbid "work, short gap,
work"), minimum stretch (forbid "free, short run, free", with an escape variable per
matching short piece of demand). Helpers: `_blocks_of_day`, `_variables_of`,
`_short_pieces` in rules.py; `runs_of_consecutive_blocks` in model.py (shared, tested).
Now working on **several days (option A)**: constants and `Settings.days` done, model.py
has a module docstring and class docstrings. The time helpers are stubs with 10 tests in
test_time_blocks.py: test run is 28 passed, 8 failed (the 8 red time tests, as
intended). Next session: the user implements `block_of`, `time_of`, `day_of`; Claude
reviews. Then the rename of `_blocks_of_day` and a cross-day solver test (see roadmap).
Claude reviews and explains; only changes code when asked.

## Step 2 plan: work stretches and breaks

Blocks: 1 block = 15 min, 4 = 60 min, 12 = 180 min. One day only for now.

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
