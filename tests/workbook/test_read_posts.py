import openpyxl
import pytest
from openpyxl.worksheet.worksheet import Worksheet

from scheduler.model import Post
from scheduler.workbook import WorkbookError, read_posts


# Like the real Posts tab: Group, Colour and Notes are there but not read yet.
HEADER = ("Post", "Group", "Colour", "Notes")


def _posts_sheet(rows: list[tuple], header: tuple[str, ...] = HEADER) -> Worksheet:
    """A new in-memory sheet called Posts: the header in row 1, then one row per post."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active          # a new workbook always has one sheet
    sheet.title = "Posts"            # so the error messages can name the tab
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    return sheet


def test_each_row_gives_a_post_in_the_order_of_the_sheet():
    """Every row becomes a Post, in the same order as on the tab."""
    # Arrange
    rows = [("Tickets",   "Ticketing", "C9DAF8"),
            ("Infobooth", "Infobooth", "D9EAD3")]
    sheet = _posts_sheet(rows)

    # Act
    posts = read_posts(sheet)

    # Assert
    assert posts == [Post(name="Tickets"), Post(name="Infobooth")]


def test_spaces_around_a_post_name_are_removed():
    """" Tickets " becomes "Tickets", so it matches the name on the other tabs."""
    # Arrange
    rows = [(" Tickets ", "Ticketing", "C9DAF8")]
    sheet = _posts_sheet(rows)

    # Act
    posts = read_posts(sheet)

    # Assert
    assert posts == [Post(name="Tickets")]


def test_empty_rows_are_skipped():
    """A completely empty row between the posts is no problem."""
    # Arrange
    rows = [("Tickets",   "Ticketing", "C9DAF8"),
            (),                                    # an empty row
            ("Infobooth", "Infobooth", "D9EAD3")]
    sheet = _posts_sheet(rows)

    # Act
    posts = read_posts(sheet)

    # Assert
    assert posts == [Post(name="Tickets"), Post(name="Infobooth")]


def test_missing_post_column_raises_workbook_error():
    """A Posts tab without a Post column is an error."""
    # Arrange
    header = ("Name", "Group", "Colour", "Notes")   # "Name" instead of "Post"
    rows = [("Tickets", "Ticketing", "C9DAF8")]
    sheet = _posts_sheet(rows, header=header)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Posts.*Post"):
        read_posts(sheet)


def test_the_same_post_twice_raises_workbook_error():
    """Two rows with the same post are an error naming the post."""
    # Arrange
    rows = [("Tickets", "Ticketing", "C9DAF8"),
            ("Tickets", "Ticketing", "C9DAF8")]
    sheet = _posts_sheet(rows)

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Tickets"):
        read_posts(sheet)


def test_tab_without_posts_raises_workbook_error():
    """A Posts tab with only a header is an error: nothing can be scheduled without posts."""
    # Arrange
    sheet = _posts_sheet([])

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while the call runs.)

    # Assert
    with pytest.raises(WorkbookError, match="Posts"):
        read_posts(sheet)
