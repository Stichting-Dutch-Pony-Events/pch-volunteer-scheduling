# pch-volunteer-scheduling

A tool to (semi-)automatically make the volunteer schedule for **PonyCon Holland**.

Making the schedule by hand takes about three days. This tool takes over the puzzle:
who works which post at what time, taking into account

- which posts need how many people, and when;
- which volunteers can do which post, and what they prefer;
- events volunteers (really) want to attend, so they get a break then;
- lunch and dinner breaks for everyone;
- not overworking anyone, and spreading the work fairly.

The puzzle itself is solved by [Google OR-Tools](https://developers.google.com/optimization)
(the CP-SAT solver). We describe the rules; the solver finds a schedule that follows them.

## Status

Version 1.0 is done: it makes a schedule from the real input workbook that follows the
hard rules, run from the command line (input workbook in, schedule in Excel out).
Version 1.1 is in development.

### Done

- [x] Project structure
- [x] Draft input workbook (made from the 2026 schedule, kept local)
- [x] Basic hard rules: every post gets exactly the people it needs, only qualified
      volunteers, nobody in two places at once
- [x] Work stretches (continuous work) between 1 and 3 hours, breaks of at least
      30 minutes; the limits are settings
- [x] Time across the whole weekend, including night shifts after midnight
- [x] Availability: volunteers are only scheduled when they are there (whole days or
      a time range)
- [x] Reading the input workbook, with clear errors for typos
- [x] Volunteers stay at their post during a work stretch (they only move on when
      their post needs fewer people)
- [x] Writing the schedule to Excel: a schedule per post with nicknames
- [x] Running it from the command line

### Roadmap to version 1.0

Version 1.0 makes a schedule from the real input workbook that follows the main hard
rules (meal breaks come later), including a maximum number of hours per volunteer, run
from the command line. Details can then be fixed by hand.

- [x] Faster: a run on the real data takes seconds instead of minutes
- [x] A clear message when no schedule is possible, saying where it gets stuck
- [x] A maximum number of hours per volunteer, per day and in total
- [x] Warnings for likely mistakes in the input, e.g. a volunteer who can never be scheduled
- [x] A time limit for the solver, so a big run can't hang
- [x] First run on real data, compared with the hand-made 2026 schedule
- [x] Small tidy-ups: a clear error for a damaged workbook, a few extra tests

### Roadmap to version 1.1

Version 1.1 makes the schedule nicer and easier to read.

- [x] Tidy the code into smaller parts (reading, solving, writing)
- [ ] Nicer schedules: shifts start and end on the hour or half hour, staying at one
      post, preferring what people are good at, shifts of preferably at most 2 hours,
      and a fair spread of work over the volunteers
- [ ] A nicer command line: progress while solving, a summary after the run
- [ ] Individual schedules in the output: per volunteer their shifts

### Later

- [ ] Maybe: shifts placed by hand are kept, e.g. to re-run after a change without
      reshuffling everyone (to decide after the first real run)
- [ ] Meal breaks
- [ ] Maybe: check any schedule against the rules, also one changed by hand afterwards
- [ ] Event wishes (REALLY want / would like to attend), read from the form answers
- [ ] More output: a "no double booking" check tab
- [ ] Choose the times the schedule shows (e.g. 08:00-02:00), instead of only the open hours
- [ ] More command line options
- [ ] All input errors shown at once, instead of stopping at the first one
- [ ] Maybe: also read `.ods` files (LibreOffice / Nextcloud); for now save as `.xlsx`
- [ ] A small program with a window: pick the input workbook, start a run, see errors

## How it works

```
Input workbook (.xlsx)  (later also the form answers, .csv)
                  │
                  ▼
        scheduler/reading/     reads each tab, checks for typos
                  │
                  ▼
        scheduler/model.py     plain data: volunteers, posts, demand, settings
                  │
                  ▼
        scheduler/solving/     checks the input, builds a CP-SAT model with the
                               rules (one function each) and solves it
                  │
                  ▼
        scheduler/writing/     writes the output workbook (.xlsx)
```

The input workbook has these tabs: ReadMe, Settings, Volunteers, Posts, Skills, Events,
Demand, Wishes and Fixed. The ReadMe tab inside the workbook explains each one.
Time is planned in 15-minute blocks; times after midnight belong to the convention day
before (Saturday 01:00 is the Saturday night).

## Project structure

```
pch-volunteer-scheduling/
├── ReferenceDocuments/      real data, NOT in git (see Privacy)
├── scheduler/
│   ├── __main__.py          the command line (python -m scheduler ...)
│   ├── errors.py            the error types
│   ├── helpers.py           debug output (--debug-time)
│   ├── model.py             data classes and time helpers
│   ├── reading/             reads the input workbook, one module per tab
│   ├── solving/             checks the input, the rules, builds and solves the schedule
│   └── writing/             writes the output workbook, one module per tab
├── templates/               an empty input workbook to start from
├── tests/
│   ├── command_line/        tests of the command line
│   ├── data/                small made-up input workbook for the tests
│   ├── model/               tests of the data classes and time helpers
│   ├── reading/             tests of reading the input workbook
│   ├── solving/             tests of the solver and its rules
│   ├── writing/             tests of writing the output workbook
│   └── test_helpers.py
├── requirements.txt
└── README.md
```

## Privacy

The form answers contain e-mail addresses and real names, and the schedules contain
everyone's nicknames. **No real volunteer data goes into this repository.**
`.gitignore` excludes `ReferenceDocuments/` and all `.ods`, `.xlsx` and `.csv` files.
The tests only use small, made-up examples.

## Development

This project is built test-first: for every step we first write tests that describe the
new behaviour, see them fail, then write just enough code to make them pass.

### Setup (Windows)

Requires Python 3.14 (OR-Tools has no wheels for 3.15 yet).

```powershell
cd C:\repos\pch-volunteer-scheduling
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Making a schedule

```powershell
python -m scheduler input.xlsx output.xlsx
```

Reads the input workbook, makes a schedule and writes it to `output.xlsx` (tab
"Schedule": one column per post, one row per 15 minutes). If the output already
exists you are asked before it is overwritten; add `--overwrite` to skip that
question. The solver stops after 10 minutes; give it more (or less) time with e.g.
`--time-limit 30` (in minutes). `python -m scheduler --help` shows the options. Keep real input and output
outside the repository: they contain volunteer names.

### Running the tests

```powershell
python -m pytest
```

## License

GPL-3.0, see [LICENSE](LICENSE).
