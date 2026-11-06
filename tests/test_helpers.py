import io
import re

from scheduler import helpers
from scheduler.helpers import debug_print, set_debug_time


# Every test that switches debugging on uses monkeypatch for it: monkeypatch puts the
# switch back as it was after the test, so other tests are never affected.


def test_debugging_is_off_by_default():
    """Without --debug-time, debug_print is switched off."""
    # Arrange
    # Nothing to set up: we look at the switch as the module starts with it.

    # Act
    result = helpers.debug_time_on

    # Assert
    assert result is False


def test_set_debug_time_switches_debugging_on(monkeypatch):
    """set_debug_time(True) switches debugging on."""
    # Arrange
    monkeypatch.setattr(helpers, "debug_time_on", False)

    # Act
    set_debug_time(True)

    # Assert
    assert helpers.debug_time_on is True


def test_set_debug_time_switches_debugging_off(monkeypatch):
    """set_debug_time(False) switches debugging off again."""
    # Arrange
    monkeypatch.setattr(helpers, "debug_time_on", True)

    # Act
    set_debug_time(False)

    # Assert
    assert helpers.debug_time_on is False


def test_debug_print_writes_the_message_when_debugging_is_on(monkeypatch):
    """With debugging on, the message is written to the destination."""
    # Arrange
    monkeypatch.setattr(helpers, "debug_time_on", True)
    # io.StringIO acts like a file that keeps everything written to it in memory.
    destination = io.StringIO()

    # Act
    debug_print("Building the model", destination)

    # Assert
    assert "Building the model" in destination.getvalue()


def test_debug_print_starts_with_a_tab_and_the_time_in_milliseconds(monkeypatch):
    """The line starts with a tab and the time to the millisecond, e.g. [14:03:12.345]."""
    # Arrange
    monkeypatch.setattr(helpers, "debug_time_on", True)
    destination = io.StringIO()

    # Act
    debug_print("Building the model", destination)

    # Assert
    # A tab, "[", hours, ":", minutes, ":", seconds, ".", three digits, "] ", then the
    # message.
    assert re.fullmatch(r"\t\[\d\d:\d\d:\d\d\.\d{3}\] Building the model\n",
                        destination.getvalue())


def test_debug_print_writes_nothing_when_debugging_is_off(monkeypatch):
    """With debugging off, nothing is written at all."""
    # Arrange
    monkeypatch.setattr(helpers, "debug_time_on", False)
    destination = io.StringIO()

    # Act
    debug_print("Building the model", destination)

    # Assert
    assert destination.getvalue() == ""


def test_debug_print_writes_to_stdout_by_default(monkeypatch, capsys):
    """Without a destination, the line goes to normal output (stdout)."""
    # Arrange
    monkeypatch.setattr(helpers, "debug_time_on", True)

    # Act
    debug_print("Building the model")

    # Assert
    assert "Building the model" in capsys.readouterr().out
