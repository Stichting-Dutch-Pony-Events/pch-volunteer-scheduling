"""The command line: python -m scheduler input.xlsx output.xlsx [--overwrite]

Python runs this file when you type "python -m scheduler". All the work happens in main(),
which takes the arguments as a list, so the tests can call it directly without a terminal.
"""
import sys

from scheduler.output import write_output
from scheduler.solver import NoScheduleFound, solve
from scheduler.workbook import WorkbookError, read_problem


def main(arguments: list[str]) -> int:
    """Read the input workbook, solve it and write the output. Returns the exit code.

    0 = schedule written, 1 = something went wrong (a clear message is printed to stderr).
    Cheap checks come first, so a wrong output name doesn't wait for the solver: the output
    must be .xlsx, must not be the input file, and its folder must exist. An existing output
    is only overwritten after the user answers y/yes, or with --overwrite.
    """
    raise NotImplementedError  # stub, so the tests can run and fail


if __name__ == "__main__":
    # sys.argv[0] is the program itself; the rest are the words typed after it.
    sys.exit(main(sys.argv[1:]))
