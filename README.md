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

Early development. Nothing runs yet.

- [x] Project structure
- [x] Draft input workbook (made from the 2026 schedule, kept local)
- [ ] Step 1: minimal solver with the basic hard rules (demand met, only qualified volunteers, no double booking)
- [ ] Shift lengths (minimum 1 hour, preferably at most 2, never more than 3)
- [ ] Meal breaks
- [ ] Event wishes (REALLY want / would like to attend)
- [ ] Maximum hours and a fair spread of work
- [ ] Reading the input workbook and the form CSV
- [ ] Writing the schedule to Excel (overview, per post, per volunteer)

## How it works (planned)

```
Input workbook (.xlsx)  +  form answers (.csv)
                  │
                  ▼
        scheduler/model.py     plain data: volunteers, posts, demand, events, wishes
                  │
                  ▼
        scheduler/solver.py    turns the rules into a CP-SAT model and solves it
                  │
                  ▼
        Output workbook (.xlsx)  printable schedules
```

The input workbook has these tabs: ReadMe, Settings, Meals, Volunteers, Posts, Skills,
Events, Demand, Wishes and Fixed. The ReadMe tab inside the workbook explains each one.
Time is planned in 15-minute blocks; times after midnight belong to the convention day
before (Saturday 01:00 is the Saturday night).

## Project structure

```
pch-volunteer-scheduling/
├── ReferenceDocuments/      real data, NOT in git (see Privacy)
├── scheduler/
│   ├── hello.py             setup check (Python, pytest and OR-Tools work)
│   ├── model.py             data classes
│   └── solver.py            builds and solves the schedule
├── tests/
│   ├── test_hello.py
│   └── test_solver_basics.py
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

### Running the tests

```powershell
python -m pytest
```

## License

GPL-3.0, see [LICENSE](LICENSE).
