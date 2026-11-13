"""Reads the Volunteers tab: read_volunteers, then the helpers only it uses."""
from openpyxl.worksheet.worksheet import Worksheet

from scheduler.debug import debug_print
from scheduler.errors import WorkbookError
from scheduler.model import Settings, Volunteer
from scheduler.reading.cells import cell_text, find_columns, parse_availability, parse_hour_limits


def read_volunteers(sheet: Worksheet, settings: Settings) -> dict[str, Volunteer]:
    """The Volunteers tab as {nickname: Volunteer}, in the order of the sheet.

    Reads the Nickname column, one availability column per day in settings.days and the
    columns Max hours per day and Max hours total (a missing column is an error). Each
    day's cell goes through parse_availability and the days are combined. An hour limit
    is whole hours or "none" (no limit); an empty cell gets the default from the
    settings. Skills stay empty here: read_problem adds them from the Skills tab. A
    completely empty row is skipped. Raises WorkbookError (naming row, volunteer and day
    or column where possible) for a missing column, a nickname used twice, a row with
    values but no nickname, an invalid availability or hour limit, a volunteer who is not
    available on any day, or a written per day limit above the written total.
    """
    debug_print(f"read_volunteers: reading tab {sheet.title}")
    # 1. The Nickname column, one column per convention day and the two hour limit columns.
    limit_columns = ["Max hours per day", "Max hours total"]
    columns = find_columns(sheet, ["Nickname"] + list(settings.days) + limit_columns)

    volunteers = {}
    for row in range(2, sheet.max_row + 1):
        nickname = cell_text(sheet.cell(row=row, column=columns["Nickname"]).value)

        # 2. The cells of this row: availability per day {"Friday": "yes", ...} and the
        #    hour limits {"Max hours per day": "8", ...}
        availability = {}
        for day in settings.days:
            availability[day] = cell_text(sheet.cell(row=row, column=columns[day]).value)
        hour_limits = {}
        for name in limit_columns:
            hour_limits[name] = cell_text(sheet.cell(row=row, column=columns[name]).value)

        # 3. A row without nickname is only fine when it is completely empty.
        if nickname == "":
            for day in settings.days:
                if availability[day] != "":
                    raise WorkbookError(f"Volunteers, row {row}: availability but no nickname.")
            for name in limit_columns:
                if hour_limits[name] != "":
                    raise WorkbookError(f"Volunteers, row {row}: {name} but no nickname.")
            continue  # an empty row: skip it

        if nickname in volunteers:
            raise WorkbookError(f"Volunteers, row {row}: the nickname {nickname!r} is used "
                                f"more than once.")

        # 4. The blocks they are available, and their hour limits.
        blocks = _available_blocks_of_row(row, nickname, availability, settings)
        max_minutes_per_day, max_minutes_total = _hour_limits_of_row(row, nickname,
                                                                     hour_limits, settings)

        # Skills are on another tab: read_problem fills them in.
        volunteers[nickname] = Volunteer(name=nickname,
                                         skills={},
                                         available_blocks=blocks,
                                         max_minutes_per_day=max_minutes_per_day,
                                         max_minutes_total=max_minutes_total)

    return volunteers


def _available_blocks_of_row(row: int, nickname: str, availability: dict[str, str],
                             settings: Settings) -> set[int]:
    """All blocks one volunteer is available, from their cells {day: text} on Volunteers.

    Each day's text goes through parse_availability; the days are combined. Raises
    WorkbookError naming row, volunteer and day for an invalid availability, and for a
    volunteer who is not available on any day. row and nickname are for the messages.
    """
    blocks = set()
    for day in settings.days:
        try:
            # | combines two sets.
            blocks = blocks | parse_availability(availability[day], day, settings)
        except ValueError as error:
            # Put row, volunteer and day in front of the message from parse_availability.
            raise WorkbookError(f"Volunteers, row {row} ({nickname}), {day}: {error}") from None

    if len(blocks) == 0:
        raise WorkbookError(f"Volunteers, row {row}: {nickname} is not available on any day. "
                            f"Remove the row if they are not coming.")

    return blocks


def _hour_limits_of_row(row: int, nickname: str, hour_limits: dict[str, str],
                        settings: Settings) -> tuple[int | None, int | None]:
    """One volunteer's (per day, total) hour limits in minutes, None = no limit.

    hour_limits holds their cells {"Max hours per day": text, "Max hours total": text}.
    A written cell goes through parse_hour_limits (whole hours or "none"; the two are only
    compared when both are written as a number); an empty cell gets the default from the
    settings. Raises WorkbookError naming row and volunteer. row and nickname are for the
    messages.
    """
    per_day_text = hour_limits["Max hours per day"]
    total_text = hour_limits["Max hours total"]
    try:
        max_minutes_per_day, max_minutes_total = parse_hour_limits(
            ("Max hours per day", per_day_text),
            ("Max hours total", total_text),
            len(settings.days))
    except ValueError as error:
        # Put tab, row and volunteer in front of the message from parse_hour_limits.
        raise WorkbookError(f"Volunteers, row {row} ({nickname}), {error}") from None

    # An empty cell gets the default from the settings (parse_hour_limits gave None for it).
    if per_day_text == "":
        max_minutes_per_day = settings.default_max_minutes_per_day
    if total_text == "":
        max_minutes_total = settings.default_max_minutes_total

    return max_minutes_per_day, max_minutes_total
