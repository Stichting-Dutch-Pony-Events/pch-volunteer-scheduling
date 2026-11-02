import openpyxl
import pytest
from openpyxl.worksheet.worksheet import Worksheet

from scheduler.workbook import WorkbookError, read_skills


# Like the Skills tab of the test workbook: Team is there but not a post.
HEADER = ("Nickname", "Team", "Tickets", "Infobooth", "Security - Downstairs")


def _skills_sheet(rows: list[tuple], header: tuple[str, ...] = HEADER) -> Worksheet:
    """A new in-memory sheet called Skills: the header in row 1, then one row per volunteer."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active          # a new workbook always has one sheet
    sheet.title = "Skills"           # so the error messages can name the tab
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    return sheet


def test_each_volunteer_gets_their_score_per_post():
    """Every volunteer gets a score for each post they have a number for."""
    # Arrange
    rows = [("Mock Mane",    "Ticketing", 3, 1, 2),
            ("Testy Hooves", "Infobooth", 1, 3, 1)]
    sheet = _skills_sheet(rows)

    # Act
    skills = read_skills(sheet)

    # Assert
    assert skills == {"Mock Mane": {"Tickets": 3, "Infobooth": 1, "Security - Downstairs": 2},
                      "Testy Hooves": {"Tickets": 1, "Infobooth": 3, "Security - Downstairs": 1}}


def test_an_empty_cell_means_never_and_is_left_out():
    """A post without a score is not in the volunteer's skills at all."""
    # Arrange
    rows = [("Dummy Dash", "Ticketing", 2, None, None)]   # None = an empty cell
    sheet = _skills_sheet(rows)

    # Act
    skills = read_skills(sheet)

    # Assert
    assert skills == {"Dummy Dash": {"Tickets": 2}}


def test_a_score_typed_as_text_is_accepted():
    """A score stored as text, e.g. after copy and paste, counts the same as a number."""
    # Arrange
    rows = [("Mock Mane", "Ticketing", "2", None, None)]
    sheet = _skills_sheet(rows)

    # Act
    skills = read_skills(sheet)

    # Assert
    assert skills == {"Mock Mane": {"Tickets": 2}}


def test_team_and_notes_columns_are_not_posts():
    """The Team and Notes columns are not read as posts, whatever is in them."""
    # Arrange
    header = HEADER + ("Notes",)   # a tuple with one item needs the comma
    rows = [("Mock Mane", "Ticketing", 3, None, None, "Prefers mornings")]
    sheet = _skills_sheet(rows, header=header)

    # Act
    skills = read_skills(sheet)

    # Assert
    assert skills == {"Mock Mane": {"Tickets": 3}}


def test_empty_header_cells_are_skipped():
    """An empty column between the posts is not a post."""
    # Arrange
    header = ("Nickname", "Team", "Tickets", None, "Infobooth")   # an empty header cell
    rows = [("Mock Mane", "Ticketing", 3, None, 1)]
    sheet = _skills_sheet(rows, header=header)

    # Act
    skills = read_skills(sheet)

    # Assert
    assert skills == {"Mock Mane": {"Tickets": 3, "Infobooth": 1}}


def test_empty_rows_are_skipped():
    """A completely empty row between the volunteers is no problem."""
    # Arrange
    rows = [("Mock Mane",    "Ticketing", 3, None, None),
            (),                                            # an empty row
            ("Testy Hooves", "Infobooth", None, 3, None)]
    sheet = _skills_sheet(rows)

    # Act
    skills = read_skills(sheet)

    # Assert
    assert skills == {"Mock Mane": {"Tickets": 3}, "Testy Hooves": {"Infobooth": 3}}


def test_volunteer_without_any_score_raises_workbook_error():
    """A volunteer who may do no post at all is an error naming the volunteer."""
    # Arrange
    rows = [("Mock Mane", "Ticketing", None, None, None)]
    sheet = _skills_sheet(rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Mock Mane"):
        read_skills(sheet)


def test_missing_nickname_column_raises_workbook_error():
    """A Skills tab without a Nickname column is an error."""
    # Arrange
    header = ("Name", "Team", "Tickets", "Infobooth", "Security - Downstairs")
    rows = [("Mock Mane", "Ticketing", 3, 1, None)]
    sheet = _skills_sheet(rows, header=header)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Skills.*Nickname"):
        read_skills(sheet)


def test_the_same_nickname_twice_raises_workbook_error():
    """Two rows with the same nickname are an error naming the nickname."""
    # Arrange
    rows = [("Mock Mane", "Ticketing", 3, None, None),
            ("Mock Mane", "Ticketing", None, 1, None)]
    sheet = _skills_sheet(rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Mock Mane"):
        read_skills(sheet)


def test_the_same_post_column_twice_raises_workbook_error():
    """Two columns for the same post are an error naming the post."""
    # Arrange
    header = ("Nickname", "Team", "Tickets", "Infobooth", "Tickets")
    rows = [("Mock Mane", "Ticketing", 3, 1, 3)]
    sheet = _skills_sheet(rows, header=header)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Tickets"):
        read_skills(sheet)


@pytest.mark.parametrize(
    "score",
    [4, 0, "x", 1.5],
    ids=["too high", "zero", "text", "decimal"])
def test_invalid_score_raises_workbook_error_naming_volunteer_and_post(score):
    """A score that is not empty, 1, 2 or 3 is an error naming the volunteer and the post."""
    # Arrange
    rows = [("Mock Mane", "Ticketing", 3, score, None)]   # the invalid score is at Infobooth
    sheet = _skills_sheet(rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Mock Mane.*Infobooth"):
        read_skills(sheet)


def test_row_with_scores_but_no_nickname_raises_workbook_error():
    """A row with scores but no nickname is an error naming the row."""
    # Arrange
    rows = [(None, "Ticketing", 1, 1, 1)]   # the nickname was forgotten
    sheet = _skills_sheet(rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Skills.*row 2"):   # row 1 is the header
        read_skills(sheet)
