"""The volunteer scheduler: an input workbook in, a schedule workbook out.

Where to find what, in the order a run goes through them:

    __main__.py   the command line (python -m scheduler input.xlsx output.xlsx): main()
    workbook.py   reads the input workbook into a Problem: read_problem() and a reader per tab
    solver.py     builds the CP-SAT model and solves it: solve()
    rules.py      the hard rules, one add_<name>_rule() function each
    output.py     writes the schedule workbook: write_output() and create_<name>_sheet()

Used by all of them:

    model.py      the data (Volunteer, Post, Settings, Problem, Schedule) and the time
                  helpers (block_of, time_of, day_of, all_blocks)
    errors.py     the error types (WorkbookError, NoScheduleFound)
    helpers.py    debug_print() for --debug-time
"""
