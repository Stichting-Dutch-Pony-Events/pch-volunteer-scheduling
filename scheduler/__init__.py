"""The volunteer scheduler: an input workbook in, a schedule workbook out.

Where to find what, in the order a run goes through them:

    __main__.py   the command line (python -m scheduler input.xlsx output.xlsx): main()
    workbook.py   reads the input workbook into a Problem: read_problem() and a reader per tab
    solving/      checks the problem, builds the CP-SAT model and solves it: solver.py
                  (solve), checks.py (check_problem, find_warnings), variables.py,
                  hard_rules.py
    writing/      writes the output workbook: output.py (write_output), schedule_sheet.py

Used by all of them:

    model.py      the data (Volunteer, Post, Settings, Problem, Schedule) and the time
                  helpers (block_of, time_of, day_of, all_blocks)
    errors.py     the error types (WorkbookError, NoScheduleFound and its children)
    helpers.py    debug_print() for --debug-time
"""
