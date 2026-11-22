import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import openpyxl
import pytest

import scheduler.__main__ as command_line
from scheduler import debug
from scheduler.errors import NoScheduleFound, TimeLimitReached
from scheduler.model import Problem, Schedule


TEST_WORKBOOK = Path(__file__).parent.parent / "data" / "test_input.xlsx"
REPOSITORY = Path(__file__).parent.parent.parent


def _fail_if_called(*arguments, **keywords) -> None:
    """Stands in for a function that must not be called in this test.

    *arguments and **keywords accept any arguments, positional or by name (problem=...).
    """
    raise AssertionError("This function should not have been called.")


def _existing_output(folder: Path) -> Path:
    """An output.xlsx that is already there, with one tab called "Old"."""
    path = folder / "output.xlsx"
    old_workbook = openpyxl.Workbook()
    old_workbook.active.title = "Old"
    old_workbook.save(path)
    return path


# --- normal runs ---

def test_writes_the_schedule_and_returns_0(tmp_path):
    """A normal run on the test workbook writes the output file and returns exit code 0."""
    # Arrange
    output = tmp_path / "output.xlsx"

    # Act
    result = command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    assert result == 0
    assert output.exists()


def test_success_message_names_the_output_file(tmp_path, capsys):
    """After a normal run the program says where the schedule was written."""
    # Arrange
    output = tmp_path / "output.xlsx"

    # Act
    command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    # capsys catches everything that was printed: .out for normal output, .err for errors.
    printed = capsys.readouterr()
    assert "output.xlsx" in printed.out


def test_progress_messages_show_each_step_in_order(tmp_path, capsys):
    """While running, the program says it is reading, solving and writing, in that order."""
    # Arrange
    output = tmp_path / "output.xlsx"

    # Act
    command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    printed = capsys.readouterr().out
    reading = printed.index("Reading")    # .index raises ValueError if the word is missing
    solving = printed.index("Solving")
    writing = printed.index("Writing")
    assert reading < solving < writing


def test_solved_message_comes_between_solving_and_writing(tmp_path, capsys):
    """Right after solving, the program says it is solved and how long that took."""
    # Arrange
    output = tmp_path / "output.xlsx"

    # Act
    command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    printed = capsys.readouterr().out
    solving = printed.index("Solving")
    solved = printed.index("Solved, this took ")
    writing = printed.index("Writing")
    assert solving < solved < writing


@pytest.mark.parametrize("seconds, expected_text", [
    (3.24, "3.2 s"),
    (0.04, "0.0 s"),
    (75, "1 min 15 s"),
    (312.4, "5 min 12 s"),
    (119.6, "2 min 0 s"),
])
def test_format_duration_gives_seconds_or_minutes_and_seconds(seconds, expected_text):
    """Under a minute in seconds with one decimal, from a minute in whole minutes and seconds."""
    # Arrange
    # Nothing to set up: the seconds and the expected text come from parametrize.

    # Act
    result = command_line.format_duration(seconds)

    # Assert
    assert result == expected_text


def test_progress_messages_start_with_the_time(tmp_path, capsys):
    """Every line the program prints during a normal run starts with the time, e.g. [14:03:12]."""
    # Arrange
    output = tmp_path / "output.xlsx"

    # Act
    command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    # A regular expression: "[", two digits, ":", two digits, ":", two digits, "] ".
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) > 0
    for line in lines:
        assert re.match(r"\[\d\d:\d\d:\d\d\] ", line), line


def test_missing_arguments_stop_with_a_usage_message():
    """Without an output file name argparse stops the program with exit code 2."""
    # Arrange
    # Nothing to set up: only the input file is given, the output is missing.

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    # argparse doesn't return: it prints the usage and raises SystemExit itself.
    with pytest.raises(SystemExit) as stop:
        command_line.main([str(TEST_WORKBOOK)])
    assert stop.value.code == 2


# --- checks on the output name, before solving ---

def test_output_that_is_not_xlsx_is_refused_before_solving(tmp_path, monkeypatch, capsys):
    """An output name that doesn't end in .xlsx gives exit code 1 without solving first."""
    # Arrange
    monkeypatch.setattr(command_line, "solve", _fail_if_called)

    # Act
    result = command_line.main([str(TEST_WORKBOOK), str(tmp_path / "output.ods")])

    # Assert
    assert result == 1
    assert ".xlsx" in capsys.readouterr().err


def test_output_that_is_the_input_file_is_refused(tmp_path, monkeypatch):
    """Writing the output over the input is refused and leaves the input untouched."""
    # Arrange
    # A copy, so a bug can never damage the real test workbook.
    input_file = tmp_path / "input.xlsx"
    shutil.copy(TEST_WORKBOOK, input_file)
    content_before = input_file.read_bytes()
    monkeypatch.setattr("builtins.input", _fail_if_called)

    # Act
    result = command_line.main([str(input_file), str(input_file), "--overwrite"])

    # Assert
    assert result == 1
    assert input_file.read_bytes() == content_before


def test_output_folder_that_does_not_exist_prints_a_clear_message(tmp_path, monkeypatch,
                                                                  capsys):
    """An output in a folder that doesn't exist gives exit code 1 and names the folder."""
    # Arrange
    monkeypatch.setattr(command_line, "solve", _fail_if_called)
    output = tmp_path / "no_such_folder" / "output.xlsx"

    # Act
    result = command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    assert result == 1
    assert "no_such_folder" in capsys.readouterr().err


# --- overwriting an existing output ---

@pytest.mark.parametrize("answer", ["y", "yes", "Y"])
def test_existing_output_is_overwritten_when_the_user_says_yes(tmp_path, monkeypatch, answer):
    """Answering y or yes to the question overwrites the existing output."""
    # Arrange
    output = _existing_output(tmp_path)

    # monkeypatch replaces input() during this test: it "types" the answer.
    def fake_input(question: str) -> str:
        return answer
    monkeypatch.setattr("builtins.input", fake_input)

    # Act
    result = command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    assert result == 0
    assert openpyxl.load_workbook(output).sheetnames == ["Schedule"]


@pytest.mark.parametrize("answer", ["n", "", "maybe"])
def test_existing_output_is_kept_when_the_user_does_not_say_yes(tmp_path, monkeypatch,
                                                                answer):
    """Any answer other than y/yes (also just Enter) leaves the file alone, exit code 1."""
    # Arrange
    output = _existing_output(tmp_path)
    content_before = output.read_bytes()

    def fake_input(question: str) -> str:
        return answer
    monkeypatch.setattr("builtins.input", fake_input)

    # Act
    result = command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    assert result == 1
    assert output.read_bytes() == content_before


def test_overwrite_flag_skips_the_question(tmp_path, monkeypatch):
    """With --overwrite an existing output is replaced without asking."""
    # Arrange
    output = _existing_output(tmp_path)
    monkeypatch.setattr("builtins.input", _fail_if_called)

    # Act
    result = command_line.main([str(TEST_WORKBOOK), str(output), "--overwrite"])

    # Assert
    assert result == 0
    assert openpyxl.load_workbook(output).sheetnames == ["Schedule"]


def test_no_question_when_the_output_does_not_exist_yet(tmp_path, monkeypatch):
    """A new output file is written without asking anything."""
    # Arrange
    monkeypatch.setattr("builtins.input", _fail_if_called)

    # Act
    result = command_line.main([str(TEST_WORKBOOK), str(tmp_path / "output.xlsx")])

    # Assert
    assert result == 0


# --- warnings before solving ---

def _one_warning(problem: Problem) -> list[str]:
    """Stands in for find_warnings: always one warning, whatever the workbook says."""
    return ["Mock Mane can never be scheduled"]


def test_warnings_are_printed_before_solving(tmp_path, monkeypatch, capsys):
    """Each warning is printed with "Warning: " in front, before the program starts solving."""
    # Arrange
    # Every volunteer in the test workbook can be scheduled, so find_warnings pretends.
    monkeypatch.setattr(command_line, "find_warnings", _one_warning)
    output = tmp_path / "output.xlsx"

    # Act
    command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    printed = capsys.readouterr().out
    warning = printed.index("Warning: Mock Mane can never be scheduled")
    solving = printed.index("Solving")
    assert warning < solving


def test_run_carries_on_after_a_warning(tmp_path, monkeypatch):
    """A warning does not stop the run: the schedule is still written, exit code 0."""
    # Arrange
    monkeypatch.setattr(command_line, "find_warnings", _one_warning)
    output = tmp_path / "output.xlsx"

    # Act
    result = command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    assert result == 0
    assert output.exists()


# --- time limit ---

def _remember_time_limit(monkeypatch: pytest.MonkeyPatch) -> dict[str, int | None]:
    """Replace solve with a fake that remembers the time limit it got, then stops the run.

    Returns the dict the fake fills in, so the test can look at it after main() is done.
    """
    received = {}

    def fake_solve(problem: Problem, time_limit_seconds: int | None,
                   on_first_schedule: Callable[[float, int], None] | None = None,
                   on_stopping: Callable[[], None] | None = None) -> Schedule:
        received["time_limit_seconds"] = time_limit_seconds
        raise NoScheduleFound("stop here")   # no need to really solve and write
    monkeypatch.setattr(command_line, "solve", fake_solve)
    return received


def test_time_limit_flag_is_passed_to_solve_in_seconds(tmp_path, monkeypatch):
    """--time-limit 20 (minutes) reaches solve() as 1200 seconds."""
    # Arrange
    received = _remember_time_limit(monkeypatch)
    output = tmp_path / "output.xlsx"

    # Act
    command_line.main([str(TEST_WORKBOOK), str(output), "--time-limit", "20"])

    # Assert
    assert received["time_limit_seconds"] == 1200


def test_without_time_limit_flag_solve_gets_ten_minutes(tmp_path, monkeypatch):
    """Without --time-limit, solve() gets the default of 10 minutes (600 seconds)."""
    # Arrange
    received = _remember_time_limit(monkeypatch)
    output = tmp_path / "output.xlsx"

    # Act
    command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    assert received["time_limit_seconds"] == 600


@pytest.mark.parametrize("minutes", ["0", "-5", "ten", "1.5"],
                         ids=["zero", "negative", "not a number", "not whole"])
def test_time_limit_that_is_not_a_positive_whole_number_stops_with_a_usage_message(
        tmp_path, monkeypatch, minutes):
    """A time limit of 0, below 0, not a number or not whole stops with exit code 2."""
    # Arrange
    monkeypatch.setattr(command_line, "solve", _fail_if_called)
    output = tmp_path / "output.xlsx"

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    # argparse doesn't return: it prints the usage and raises SystemExit itself.
    with pytest.raises(SystemExit) as stop:
        command_line.main([str(TEST_WORKBOOK), str(output), "--time-limit", minutes])
    assert stop.value.code == 2


def test_time_limit_reached_prints_a_clear_message(tmp_path, monkeypatch, capsys):
    """When the time limit is reached, the program says so, suggests --time-limit, exit 1."""
    # Arrange
    # A real timeout is hard to make in a test, so solve pretends.
    def fake_solve(problem: Problem, time_limit_seconds: int | None,
                   on_first_schedule: Callable[[float, int], None] | None = None,
                   on_stopping: Callable[[], None] | None = None) -> Schedule:
        raise TimeLimitReached("No schedule found within the time limit of 10 minutes.")
    monkeypatch.setattr(command_line, "solve", fake_solve)
    output = tmp_path / "output.xlsx"

    # Act
    result = command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    printed = capsys.readouterr().err
    assert result == 1
    assert "10 minutes" in printed
    assert "--time-limit" in printed


# --- the message after solving ---
# solved_message gets a Schedule made by hand, so these tests need no solving and no clock.
# Not proven optimal + solving took at least the time limit = the limit was reached;
# less than the limit = stopped by hand (Ctrl+C).

def test_optimal_schedule_says_it_is_the_best_possible():
    """A proven optimal schedule: "Solved", the time it took and its penalty."""
    # Arrange
    schedule = Schedule(assignments=set(), proven_optimal=True,
                        penalty=24, lowest_possible_penalty=24)
    expected = "Solved, this took 1 min 5 s. This is the best possible schedule (penalty 24)."

    # Act
    message = command_line.solved_message(schedule=schedule, solving_seconds=65,
                                          time_limit_seconds=600)

    # Assert
    assert message == expected


def test_time_limit_reached_gives_the_whole_message():
    """Not optimal after the whole time limit: penalty, lowest possible, percentage, advice."""
    # Arrange
    # Not optimal, 608 seconds with a limit of 600 = the limit was reached.
    # (1234 - 1100) / 1234 = 10.9%, rounded to 11.
    schedule = Schedule(assignments=set(), proven_optimal=False,
                        penalty=1234, lowest_possible_penalty=1100)
    expected = ("Time limit reached after 10 min 8 s. This is the best schedule found "
                "(penalty 1,234); the best possible has a penalty of at least 1,100 "
                "(at most 11% better). A longer --time-limit may find a better one.")

    # Act
    message = command_line.solved_message(schedule=schedule, solving_seconds=608,
                                          time_limit_seconds=600)

    # Assert
    assert message == expected


def test_stopped_before_the_time_limit_says_stopped_without_advice():
    """Not optimal before the time limit (Ctrl+C): "Stopped after", no --time-limit advice."""
    # Arrange
    # As above, but 182 seconds. Expected: "Stopped after 3 min 2 s. This is the best
    # schedule found (penalty 1,234); the best possible has a penalty of at least 1,100
    # (at most 11% better)."
    schedule = Schedule(assignments=set(), proven_optimal=False,
                        penalty=1234, lowest_possible_penalty=1100)
    expected = ("Stopped after 3 min 2 s. This is the best schedule found (penalty 1,234); "
                "the best possible has a penalty of at least 1,100 (at most 11% better).")

    # Act
    message = command_line.solved_message(schedule=schedule, solving_seconds=182,
                                          time_limit_seconds=600)

    # Assert
    assert message == expected


def test_solving_exactly_as_long_as_the_time_limit_counts_as_limit_reached():
    """Solving took exactly the time limit: the message starts with "Time limit reached"."""
    # Arrange
    # Not optimal, 600 seconds, limit 600.
    schedule = Schedule(assignments=set(), proven_optimal=False,
                        penalty=1234, lowest_possible_penalty=1100)
    expected = ("Time limit reached after 10 min 0 s. This is the best schedule found "
                "(penalty 1,234); the best possible has a penalty of at least 1,100 "
                "(at most 11% better). A longer --time-limit may find a better one.")

    # Act
    message = command_line.solved_message(schedule=schedule, solving_seconds=600,
                                          time_limit_seconds=600)

    # Assert
    assert message == expected


def test_less_than_1_percent_better_is_said_in_words():
    """Below 1%, the message says "less than 1% better" instead of "at most 0% better"."""
    # Arrange
    # Not optimal, penalty 1000, lowest possible 998 (0.2%).
    schedule = Schedule(assignments=set(), proven_optimal=False,
                        penalty=1000, lowest_possible_penalty=998)
    expected = ("Stopped after 3 min 2 s. This is the best schedule found (penalty 1,000); "
                "the best possible has a penalty of at least 998 (less than 1% better).")

    # Act
    message = command_line.solved_message(schedule=schedule, solving_seconds=182,
                                          time_limit_seconds=600)

    # Assert
    assert message == expected


def test_lowest_possible_penalty_0_gives_no_percentage():
    """A lowest possible penalty of 0 proves nothing yet, so no percentage is shown."""
    # Arrange
    # Not optimal, penalty 1000, lowest possible 0: "at least 0" and no "%".
    schedule = Schedule(assignments=set(), proven_optimal=False,
                        penalty=1000, lowest_possible_penalty=0)
    expected = ("Stopped after 3 min 2 s. This is the best schedule found (penalty 1,000); "
                "the best possible has a penalty of at least 0.")

    # Act
    message = command_line.solved_message(schedule=schedule, solving_seconds=182,
                                          time_limit_seconds=600)

    # Assert
    assert message == expected


def test_main_prints_the_message_after_solving(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                               capsys: pytest.CaptureFixture[str]):
    """main prints solved_message's text after solving."""
    # Arrange
    # Fake solve returns a not proven optimal schedule (penalty 24, lowest possible 20),
    # fake write_output does nothing. The fake returns at once, so the message starts with
    # "Stopped after"; check only the part every variant has.
    def fake_solve(problem: Problem, time_limit_seconds: int | None,
                   on_first_schedule: Callable[[float, int], None] | None = None,
                   on_stopping: Callable[[], None] | None = None) -> Schedule:
        return Schedule(assignments=set(), proven_optimal=False,
                        penalty=24, lowest_possible_penalty=20)

    def fake_write_output(problem: Problem, schedule: Schedule, path: Path) -> None:
        pass   # nothing to write: only the printed message matters here

    monkeypatch.setattr(command_line, "solve", fake_solve)
    monkeypatch.setattr(command_line, "write_output", fake_write_output)
    output = tmp_path / "output.xlsx"

    # Act
    command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    printed = capsys.readouterr().out
    assert "This is the best schedule found (penalty 24)" in printed


# --- the first schedule ---
# While CP-SAT searches for better schedules, one line says a first schedule was found and
# that Ctrl+C stops the search but keeps the best schedule so far.

def test_first_schedule_message_under_a_minute():
    """Under a minute, the first schedule line gives the seconds with one decimal."""
    # Arrange
    # (nothing to arrange: the seconds and the penalty are given straight to the function)

    # Act
    message = command_line.first_schedule_message(seconds=12.0, penalty=2345)

    # Assert
    assert message == ("Found a first schedule after 12.0 s (penalty 2,345); now looking for "
                       "better ones. Press Ctrl+C to stop and keep the best schedule so far.")


def test_first_schedule_message_over_a_minute():
    """From a minute on, the first schedule line gives minutes and seconds."""
    # Arrange
    # (nothing to arrange: the seconds and the penalty are given straight to the function)

    # Act
    message = command_line.first_schedule_message(seconds=75.0, penalty=24)

    # Assert
    assert message == ("Found a first schedule after 1 min 15 s (penalty 24); now looking for "
                       "better ones. Press Ctrl+C to stop and keep the best schedule so far.")


def test_main_prints_the_first_schedule_line_while_solving(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    """main prints the first schedule line after "Solving" and before the solved message."""
    # Arrange
    # Fake solve does what CP-SAT would do: report a first schedule (12 s, penalty 2,345)
    # through the function main gives it, then return a schedule. Fake write_output does
    # nothing.
    def fake_solve(problem: Problem, time_limit_seconds: int | None,
                   on_first_schedule: Callable[[float, int], None],
                   on_stopping: Callable[[], None] | None = None) -> Schedule:
        on_first_schedule(12.0, 2345)
        return Schedule(assignments=set(), proven_optimal=True,
                        penalty=2000, lowest_possible_penalty=2000)

    def fake_write_output(problem: Problem, schedule: Schedule, path: Path) -> None:
        pass   # nothing to write: only the printed lines matter here

    monkeypatch.setattr(command_line, "solve", fake_solve)
    monkeypatch.setattr(command_line, "write_output", fake_write_output)
    output = tmp_path / "output.xlsx"

    # Act
    command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    printed = capsys.readouterr().out
    solving_at = printed.index("Solving")
    first_schedule_at = printed.index("Found a first schedule after 12.0 s (penalty 2,345)")
    solved_at = printed.index("This is the best possible schedule (penalty 2,000)")
    assert solving_at < first_schedule_at < solved_at


# --- Ctrl+C ---
# Ctrl+C during the search stops it and keeps the best schedule so far (run_cp_sat in the
# solver). Before a first schedule, or outside the search (reading, building the model,
# writing), Ctrl+C is a normal abort: a KeyboardInterrupt that main turns into one line.

def test_solving_line_says_ctrl_c_stops_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    """The "Solving" line tells the user that Ctrl+C stops the search."""
    # Arrange
    output = tmp_path / "output.xlsx"

    # Act
    command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    printed = capsys.readouterr().out
    assert "Solving (this can take a few minutes; press Ctrl+C to stop)" in printed


def test_main_prints_the_stopping_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                       capsys: pytest.CaptureFixture[str]):
    """main prints a line right when Ctrl+C asks the search to stop."""
    # Arrange
    # Fake solve does what run_cp_sat does on Ctrl+C: call on_stopping, then return the
    # best schedule so far (not proven optimal). Fake write_output does nothing.
    def fake_solve(problem: Problem, time_limit_seconds: int | None,
                   on_first_schedule: Callable[[float, int], None] | None = None,
                   on_stopping: Callable[[], None] | None = None) -> Schedule:
        on_stopping()
        return Schedule(assignments=set(), proven_optimal=False,
                        penalty=24, lowest_possible_penalty=20)

    def fake_write_output(problem: Problem, schedule: Schedule, path: Path) -> None:
        pass   # nothing to write: only the printed lines matter here

    monkeypatch.setattr(command_line, "solve", fake_solve)
    monkeypatch.setattr(command_line, "write_output", fake_write_output)
    output = tmp_path / "output.xlsx"

    # Act
    command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    printed = capsys.readouterr().out
    solving_at = printed.index("Solving")
    stopping_at = printed.index("Stopping the search; this can take a few seconds.")
    solved_at = printed.index("This is the best schedule found (penalty 24)")
    assert solving_at < stopping_at < solved_at


@pytest.mark.parametrize("stopped_in", ["read_problem", "solve"])
def test_ctrl_c_prints_a_message_and_writes_nothing(
        stopped_in: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]):
    """Ctrl+C while reading, or before a first schedule, gives one line and exit code 1."""
    # Arrange
    # The step stopped_in is replaced by a fake that acts as if Ctrl+C was pressed:
    # it raises KeyboardInterrupt (for solve: what run_cp_sat does before a first schedule).
    def press_ctrl_c(*arguments, **keywords) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(command_line, stopped_in, press_ctrl_c)
    output = tmp_path / "output.xlsx"

    # Act
    # A KeyboardInterrupt that gets out of main would make pytest stop the whole test run;
    # catching it here turns that into a normal red test.
    try:
        result = command_line.main([str(TEST_WORKBOOK), str(output)])
    except KeyboardInterrupt:
        pytest.fail("Ctrl+C got out of main: it should print a message instead")

    # Assert
    assert result == 1
    assert capsys.readouterr().err == "Stopped by Ctrl+C. No schedule written.\n"
    assert not output.exists()


# --- debug output ---

def test_debug_time_flag_switches_debug_printing_on(tmp_path, monkeypatch):
    """With --debug-time, the program switches debug_print on."""
    # Arrange
    # monkeypatch puts the switch back as it was after this test.
    monkeypatch.setattr(debug, "debug_time_on", False)
    output = tmp_path / "output.xlsx"

    # Act
    command_line.main([str(TEST_WORKBOOK), str(output), "--debug-time"])

    # Assert
    assert debug.debug_time_on is True


def test_without_debug_time_flag_debug_printing_is_off(tmp_path, monkeypatch):
    """Without --debug-time, debug_print is switched off, even if it was on before."""
    # Arrange
    # On before the run, so the test shows that main really switches it off.
    monkeypatch.setattr(debug, "debug_time_on", True)
    output = tmp_path / "output.xlsx"

    # Act
    command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    assert debug.debug_time_on is False


def test_debug_time_flag_prints_debug_lines_from_reading_solving_and_writing(
        tmp_path, monkeypatch, capsys):
    """With --debug-time, the readers, the rules and the sheet writers each print a line."""
    # Arrange
    monkeypatch.setattr(debug, "debug_time_on", False)
    output = tmp_path / "output.xlsx"

    # Act
    command_line.main([str(TEST_WORKBOOK), str(output), "--debug-time"])

    # Assert
    # Debug lines start with "DEBUG ["; one from each part is enough to show they are there.
    debug_lines = []
    for line in capsys.readouterr().out.splitlines():
        if line.startswith("DEBUG ["):
            debug_lines.append(line)
    debug_text = "\n".join(debug_lines)
    assert "read_settings" in debug_text
    assert "add_demand_rule" in debug_text
    assert "create_schedule_sheet" in debug_text


def test_debug_time_flag_prints_debug_lines_for_the_variables_and_cp_sat(
        tmp_path, monkeypatch, capsys):
    """With --debug-time, making the variables and running CP-SAT each print a line."""
    # Arrange
    monkeypatch.setattr(debug, "debug_time_on", False)
    output = tmp_path / "output.xlsx"

    # Act
    command_line.main([str(TEST_WORKBOOK), str(output), "--debug-time"])

    # Assert
    # With these two lines the time spent building the model and in CP-SAT can be told
    # apart: the gap after the last rule is then only CP-SAT.
    debug_lines = []
    for line in capsys.readouterr().out.splitlines():
        if line.startswith("DEBUG ["):
            debug_lines.append(line)
    debug_text = "\n".join(debug_lines)
    assert "create_variables" in debug_text
    assert "running CP-SAT" in debug_text


# --- errors give one clear line and exit code 1 ---

def test_typo_in_the_workbook_prints_the_workbook_error(tmp_path, capsys):
    """A WorkbookError is printed as a message (no traceback) with exit code 1."""
    # Arrange
    # A missing input file is the easiest WorkbookError to make.
    missing = tmp_path / "missing.xlsx"

    # Act
    result = command_line.main([str(missing), str(tmp_path / "output.xlsx")])

    # Assert
    assert result == 1
    assert "missing.xlsx" in capsys.readouterr().err


def test_no_schedule_possible_prints_a_message(tmp_path, monkeypatch, capsys):
    """When the solver finds no schedule, the program says so with exit code 1."""
    # Arrange
    def fake_solve(problem: Problem, time_limit_seconds: int | None,
                   on_first_schedule: Callable[[float, int], None] | None = None,
                   on_stopping: Callable[[], None] | None = None) -> Schedule:
        raise NoScheduleFound("no schedule follows all the rules")
    monkeypatch.setattr(command_line, "solve", fake_solve)

    # Act
    result = command_line.main([str(TEST_WORKBOOK), str(tmp_path / "output.xlsx")])

    # Assert
    assert result == 1
    assert "No schedule" in capsys.readouterr().err


def test_output_open_in_excel_prints_a_clear_message(tmp_path, monkeypatch, capsys):
    """A PermissionError while writing (file open in Excel) gives a hint and exit code 1."""
    # Arrange
    # A real file open in Excel is hard to make in a test, so write_output pretends.
    def fake_write_output(problem, schedule, path):
        raise PermissionError("[Errno 13] Permission denied")
    monkeypatch.setattr(command_line, "write_output", fake_write_output)

    # Act
    result = command_line.main([str(TEST_WORKBOOK), str(tmp_path / "output.xlsx")])

    # Assert
    printed = capsys.readouterr()
    assert result == 1
    assert "output.xlsx" in printed.err
    assert "Excel" in printed.err


def test_output_open_in_excel_is_refused_before_solving(tmp_path, monkeypatch, capsys):
    """An existing output that cannot be opened (open in Excel) stops the run before solving."""
    # Arrange
    output = _existing_output(tmp_path)
    monkeypatch.setattr(command_line, "solve", _fail_if_called)

    # A file really open in Excel is hard to make in a test, so open() pretends. Setting
    # "open" on the command line module only replaces it there (Python looks in the module
    # before its built-in functions); raising=False: the module has no "open" of its own yet.
    def fake_open(*arguments, **keywords):
        raise PermissionError("[Errno 13] Permission denied")
    monkeypatch.setattr(command_line, "open", fake_open, raising=False)

    # Act
    result = command_line.main([str(TEST_WORKBOOK), str(output), "--overwrite"])

    # Assert
    assert result == 1
    assert "Excel" in capsys.readouterr().err


# --- the real command ---

def test_python_m_scheduler_runs_end_to_end(tmp_path):
    """Typing "python -m scheduler input output" really writes the schedule."""
    # Arrange
    output = tmp_path / "output.xlsx"
    # sys.executable is the Python running the tests (the one in .venv).
    command = [sys.executable, "-m", "scheduler", str(TEST_WORKBOOK), str(output)]

    # Act
    # Starts a new Python process, as if typed in a terminal in the repository folder.
    finished = subprocess.run(command, cwd=REPOSITORY, capture_output=True, text=True)

    # Assert
    assert finished.returncode == 0, finished.stderr
    assert output.exists()
