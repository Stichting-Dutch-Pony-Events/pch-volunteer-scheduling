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

## How we work (agreed, please follow)

1. **Say what you will do before doing it, and wait for an OK.** Take it slow,
   one small step at a time.
   *Exception:* `CLAUDE.md` and `ReferenceDocuments/DATA_NOTES.md` may be updated
   without asking. Keep them current when agreements, decisions or status change.
   Anything privacy-sensitive (about specific people) goes in DATA_NOTES.md, never here.
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
- **openpyxl** for reading/writing `.xlsx`. No pandas for now.
- **pytest** for tests. Later possibly **Streamlit** as a simple UI.

## Repository layout

```
ReferenceDocuments/   (not in git) real data, DATA_NOTES.md, draft input workbook
scheduler/            model.py (data classes), solver.py, hello.py (setup check)
tests/                test_hello.py, test_solver_basics.py
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
- shift length at least 60 min, at most 180 min; at most 180 min continuous work,
  also across two posts
- shifts start on the hour or half hour
- a meal break inside each meal window for everyone working around it
- availability per day; fixed shifts placed by hand are kept

Soft (weighted, tunable in Settings):
- avoid working during REALLY-want events (weight 100) and like-to-attend events (20)
- prefer higher skill scores
- prefer shifts of at most 120 min
- spread hours fairly
- (later, maybe) Question vetting, Manestage clean and Sardine duty by the same person

Time: **15-minute blocks** (the event schedule uses 15 min). Times before the day
boundary (06:00) belong to the night after that convention day (Saturday 01:00 =
Saturday night).

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
- [ ] Step 1: minimal solver with in-code test data. Hard rules: demand met exactly,
      only qualified volunteers, no double booking; clear error when infeasible
- [ ] Shift lengths
- [ ] Meal breaks
- [ ] Event wishes
- [ ] Maximum hours and fair spread
- [ ] Read input workbook and form CSV
- [ ] Write output Excel (overview, per post, per volunteer; show changes vs previous run)
- [ ] Maybe: Streamlit UI

Current position: hello world passes and is committed. Step 1 has been proposed (below)
and the user is now trying to write a Step 1 test themselves. Review their test kindly,
then continue with the proposal. Two choices were still awaiting confirmation: skills
stored inside each Volunteer, and English names in the code.

## Step 1 proposal (agreed in outline, not yet written)

Minimal scheduler, no Excel, tiny made-up data built in the tests.

`scheduler/model.py`, plain dataclasses:
```python
Volunteer(name="Mock Mane", skills={"Tickets": 3, "Infobooth": 1})
Post(name="Tickets")
Problem(volunteers=[...], posts=[...], demand={("Tickets", 0): 2, ...})
Schedule(assignments={("Mock Mane", "Tickets", 0), ...})
#   Schedule.people_at(post, block) and Schedule.posts_of(volunteer, block)
```
Time blocks are plain integers (each = 15 min) for now. Demand maps (post, block) to
people needed; missing = closed.

`scheduler/solver.py`: `solve(problem) -> Schedule` and exception `NoScheduleFound`.
One boolean variable per (volunteer, post, block) where the volunteer has a skill score
(no variable at all for unqualified combinations).

Tests in `tests/test_solver_basics.py`:
1. test_single_volunteer_fills_single_post
2. test_post_gets_exactly_the_number_needed (needs 2, 3 qualified -> exactly 2)
3. test_nobody_works_a_closed_post
4. test_volunteer_without_skill_is_never_scheduled
5. test_nobody_is_in_two_places_at_once
6. test_too_few_volunteers_raises_no_schedule_found
7. test_nobody_qualified_raises_no_schedule_found

Plan: write the test file plus empty stubs in model.py/solver.py (so tests fail on
behaviour, not on imports), user runs them (red), then implement (green).
