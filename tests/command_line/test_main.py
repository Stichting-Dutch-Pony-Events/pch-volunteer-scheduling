import re
import shutil
import subprocess
import sys
from pathlib import Path

import openpyxl
import pytest

import scheduler.__main__ as command_line
from scheduler import helpers
from scheduler.solver import NoScheduleFound


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


# --- debug output ---

def test_debug_time_flag_switches_debug_printing_on(tmp_path, monkeypatch):
    """With --debug-time, the program switches debug_print on."""
    # Arrange
    # monkeypatch puts the switch back as it was after this test.
    monkeypatch.setattr(helpers, "debug_time_on", False)
    output = tmp_path / "output.xlsx"

    # Act
    command_line.main([str(TEST_WORKBOOK), str(output), "--debug-time"])

    # Assert
    assert helpers.debug_time_on is True


def test_without_debug_time_flag_debug_printing_is_off(tmp_path, monkeypatch):
    """Without --debug-time, debug_print is switched off, even if it was on before."""
    # Arrange
    # On before the run, so the test shows that main really switches it off.
    monkeypatch.setattr(helpers, "debug_time_on", True)
    output = tmp_path / "output.xlsx"

    # Act
    command_line.main([str(TEST_WORKBOOK), str(output)])

    # Assert
    assert helpers.debug_time_on is False


def test_debug_time_flag_prints_debug_lines_from_reading_solving_and_writing(
        tmp_path, monkeypatch, capsys):
    """With --debug-time, the readers, the rules and the sheet writers each print a line."""
    # Arrange
    monkeypatch.setattr(helpers, "debug_time_on", False)
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
    def fake_solve(problem):
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
