"""The command line: python -m scheduler input.xlsx output.xlsx [--overwrite] [--debug-time]
[--time-limit MINUTES]

Python runs this file when you type "python -m scheduler". All the work happens in main(),
which takes the arguments as a list, so the tests can call it directly without a terminal.
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

from scheduler.errors import NoScheduleFound, TimeLimitReached, WorkbookError
from scheduler.debug import set_debug_time
from scheduler.reading.workbook import read_problem
from scheduler.solving.checks import find_warnings
from scheduler.solving.solver import solve
from scheduler.writing.output import write_output

# Without --time-limit, the solver stops after this many minutes.
DEFAULT_TIME_LIMIT_MINUTES = 10


def main(arguments: list[str]) -> int:
    """Read the input workbook, show warnings, solve it and write the output. Returns the
    exit code.

    Warnings (likely mistakes in the input, find_warnings) are printed here and the run
    carries on: showing things to the user is the command line's job, so the core
    functions (reading, checking, solving, writing) never print. The checks that stop a
    run are different: they are part of solve() and raise a child of NoScheduleFound, which
    travels up by itself to every caller of solve().

    0 = schedule written, 1 = something went wrong (a clear message is printed to stderr).
    Cheap checks come first, so a wrong output name doesn't wait for the solver: the output
    must be .xlsx, must not be the input file, and its folder must exist. An existing output
    is only overwritten after the user answers y/yes, or with --overwrite.
    """
    # 1. Read the arguments with argparse.
    #    First describe what the command expects; the texts are shown by --help.
    parser = argparse.ArgumentParser(
        prog="python -m scheduler",
        description="Makes a volunteer schedule from an input workbook.")
    # Without dashes: positional arguments, required and in this order.
    parser.add_argument("input", help="the input workbook (.xlsx)")
    parser.add_argument("output", help="the output workbook to write (.xlsx)")
    # With dashes: optional. store_true = True when typed, False when not.
    parser.add_argument("--overwrite", action="store_true",
                        help="replace an existing output file without asking")
    parser.add_argument("--debug-time", action="store_true",
                        help="print timing details while running")
    parser.add_argument("--time-limit", type=_positive_whole_number,
                        default=DEFAULT_TIME_LIMIT_MINUTES, metavar="MINUTES",
                        help="stop the solver after this many minutes "
                             f"(default: {DEFAULT_TIME_LIMIT_MINUTES})")

    # Then let argparse read the words. On missing or unknown arguments it prints the
    # usage and stops the program itself (SystemExit, code 2), so we never get further.
    options = parser.parse_args(arguments)

    # Always set the switch, also to False, so every run starts in a known state.
    # (argparse turns the dash into an underscore: --debug-time -> options.debug_time.)
    set_debug_time(options.debug_time)

    # Not called input/output: input() is Python's own function, which we need in step 3.
    input_path = Path(options.input)
    output_path = Path(options.output)

    # 2. Cheap checks on the output, before the slow work.
    if output_path.suffix.lower() != ".xlsx":
        print(f"The output {output_path} must be an .xlsx file.", file=sys.stderr)
        return 1

    # resolve() makes the full path, so "in.xlsx" and ".\in.xlsx" count as the same file.
    if input_path.resolve() == output_path.resolve():
        print(f"The output {output_path} is the input file; choose another name.",
              file=sys.stderr)
        return 1

    if not output_path.parent.is_dir():
        print(f"The output folder {output_path.parent} does not exist.", file=sys.stderr)
        return 1

    # 3. An existing output must be writable (not open in Excel), and is only overwritten
    #    after a y/yes (Enter = no), or with --overwrite.
    if output_path.exists():
        # Open for appending ("ab") and close again without writing: the content stays as
        # it is, but a file locked by Excel raises PermissionError. ("ab" would create a
        # missing file, hence only for an existing one.) Step 4 still catches the file
        # being opened during solving.
        try:
            with open(output_path, "ab"):
                pass
        except PermissionError:
            print(f"Cannot write {output_path}: is it open in Excel? Close it and try again.",
                  file=sys.stderr)
            return 1

    if output_path.exists() and not options.overwrite:
        answer = input(f"{output_path} already exists. Overwrite it? [y/N] ")
        if answer.strip().lower() not in ["y", "yes"]:
            print("Nothing written.", file=sys.stderr)
            return 1

    # 4. The slow work: read, solve, write. Each error gives one line on stderr (no
    #    traceback) and exit code 1. Each step first says what it does, with the time.
    try:
        _say(f"Reading {input_path}")
        problem = read_problem(path=input_path)
        # Likely mistakes in the input: shown, but the run carries on.
        for line in find_warnings(problem=problem):
            _say(f"Warning: {line}")
        _say("Solving (this can take a few minutes)")
        solving_started = time.perf_counter()   # a stopwatch: only differences matter
        schedule = solve(problem=problem, time_limit_seconds=options.time_limit * 60)
        solving_seconds = time.perf_counter() - solving_started
        _say(f"Solved, this took {format_duration(solving_seconds)}")
        _say(f"Writing {output_path}")
        write_output(problem=problem, schedule=schedule, path=output_path)
    except WorkbookError as error:
        # Its message already names the tab and row.
        print(error, file=sys.stderr)
        return 1
    except NoScheduleFound as error:
        print(f"No schedule possible: {error}", file=sys.stderr)
        return 1
    except TimeLimitReached as error:
        # Not "no schedule possible": one may exist, the solver just needs more time.
        print(f"{error} Try again with a longer limit, e.g. --time-limit "
              f"{options.time_limit * 2}.", file=sys.stderr)
        return 1
    except PermissionError:
        print(f"Cannot write {output_path}: is it open in Excel? Close it and try again.",
              file=sys.stderr)
        return 1

    # 5. Done.
    _say(f"Schedule written to {output_path}")
    return 0


def format_duration(seconds: float) -> str:
    """A duration as text: under a minute "3.2 s", from a minute on "5 min 12 s"."""
    if seconds < 60:
        return f"{seconds:.1f} s"

    # Round to whole seconds first, so 119.6 becomes 2 min 0 s and not 1 min 60 s.
    whole_seconds = round(seconds)
    minutes = whole_seconds // 60
    rest = whole_seconds % 60
    return f"{minutes} min {rest} s"


def _say(message: str) -> None:
    """Print a progress message to normal output, starting with the time: [14:03:12] ...

    flush=True shows the line right away; otherwise Python may hold it back until the
    program ends, and you would not see "Solving" while it is solving.
    """
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {message}", flush=True)


def _positive_whole_number(text: str) -> int:
    """Turn the text after --time-limit into a whole number of at least 1, for argparse."""
    try:
        number = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a whole number") from None
    if number < 1:
        raise argparse.ArgumentTypeError(f"{number} is not at least 1")
    return number


if __name__ == "__main__":
    # sys.argv[0] is the program itself; the rest are the words typed after it.
    sys.exit(main(sys.argv[1:]))
