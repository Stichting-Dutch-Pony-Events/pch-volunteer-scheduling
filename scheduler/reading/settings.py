"""Reads the Settings tab: read_settings, then the helpers only it uses."""
from openpyxl.worksheet.worksheet import Worksheet

from scheduler.debug import debug_print
from scheduler.errors import WorkbookError
from scheduler.model import DAY_STARTS_AT_HOUR, MINUTES_PER_BLOCK, SOFT_RULE_NAMES, Settings
from scheduler.reading.cells import cell_text, find_columns, parse_hour_limits, parse_whole_number

# The layout of the input workbook this scheduler reads (the "Workbook format version"
# setting). Raise it only when the workbook layout changes, e.g. a renamed setting or a
# new required column, not for every new version of the scheduler.
WORKBOOK_FORMAT_VERSION = 1

KNOWN_SETTINGS = {"Workbook format version", "Time step", "Day boundary", "Days",
                  "Shift start step", "Minimum work stretch", "Preferred maximum shift length",
                  "Maximum work stretch", "Minimum break", "Lunch window start",
                  "Lunch window end", "Lunch break length", "Dinner window start",
                  "Dinner window end", "Dinner break length", "Default maximum hours per day",
                  "Default maximum hours total", "Weight: miss a REALLY-want event",
                  "Weight: miss a like-to-attend event", "Weight: skill score 3",
                  "Weight: skill score 2", "Weight: skill score 1",
                  "Weight: shift longer than preferred", "Weight: unfair spread of hours",
                  "Weight: start or end off the half hour"}

REQUIRED_SETTINGS = {"Workbook format version", "Time step", "Day boundary", "Days",
                     "Minimum work stretch", "Maximum work stretch", "Minimum break",
                     "Default maximum hours per day", "Default maximum hours total"}


def read_settings(sheet: Worksheet) -> Settings:
    """The Settings tab as Settings: one setting per row, in the columns Setting and Value.

    The order of the rows is free. Required: Workbook format version (must be
    WORKBOOK_FORMAT_VERSION), Time step (must be 15), Day boundary (must be 06:00), Days
    (comma separated, no duplicates), Minimum work stretch, Maximum work stretch and
    Minimum break (whole numbers, in minutes), Default maximum hours per day and total
    (whole hours or "none"; at most 24 per day, 24 per day of the convention in total,
    per day not more than the total). Optional: Weight: skill score 1, 2 and 3 (points
    per time step) and Weight: start or end off the half hour (points per start or end);
    whole numbers of at least 0, a missing row or empty Value gives the default in
    Settings. Every soft rule is switched on. Settings the scheduler does not
    use yet (meals, the other weights) are accepted and ignored. Raises WorkbookError for
    a missing, empty, duplicate or unknown setting, or a value that is not allowed.
    """
    debug_print(f"read_settings: reading tab {sheet.title}")
    # 1. Every setting as text, by name; then the names: nothing unknown, nothing missing.
    unparsed_settings = _unparsed_settings(sheet)
    _check_setting_names(unparsed_settings)

    # 2. The settings that only have one allowed value for now.
    _check_settings_with_one_allowed_value(unparsed_settings)

    # 3. The days, and the default hour limits (in minutes, None = no limit).
    try:
        days = parse_days(unparsed_settings["Days"])
    except ValueError as error:
        raise WorkbookError(f"Settings, Days: {error}") from None

    per_day_name = "Default maximum hours per day"
    total_name = "Default maximum hours total"
    try:
        default_per_day, default_total = parse_hour_limits(
            (per_day_name, unparsed_settings[per_day_name]),
            (total_name, unparsed_settings[total_name]),
            len(days))
    except ValueError as error:
        # Put the tab in front of the message from parse_hour_limits.
        raise WorkbookError(f"Settings, {error}") from None

    # 4. The work stretch and break, in minutes.
    # 5. The soft rule weights, optional: missing or empty = the default in Settings.
    defaults = Settings()  # only used to look up the defaults of the optional settings
    try:
        min_stretch = parse_whole_number("Minimum work stretch",
                                         unparsed_settings["Minimum work stretch"], 0)
        max_stretch = parse_whole_number("Maximum work stretch",
                                         unparsed_settings["Maximum work stretch"], 0)
        min_break = parse_whole_number("Minimum break", unparsed_settings["Minimum break"], 0)

        weight_score_1 = _optional_whole_number_setting(
            unparsed_settings, "Weight: skill score 1", defaults.weight_skill_score_1)
        weight_score_2 = _optional_whole_number_setting(
            unparsed_settings, "Weight: skill score 2", defaults.weight_skill_score_2)
        weight_score_3 = _optional_whole_number_setting(
            unparsed_settings, "Weight: skill score 3", defaults.weight_skill_score_3)
        weight_off_round_time = _optional_whole_number_setting(
            unparsed_settings, "Weight: start or end off the half hour",
            defaults.weight_off_round_time)
    except ValueError as error:
        # Put the tab in front of the message from the parse function.
        raise WorkbookError(f"Settings, {error}") from None

    # 6. Everything together; every soft rule is switched on.
    return Settings(min_stretch_minutes=min_stretch, max_stretch_minutes=max_stretch,
                    min_break_minutes=min_break, days=days,
                    default_max_minutes_per_day=default_per_day,
                    default_max_minutes_total=default_total,
                    weight_skill_score_1=weight_score_1, weight_skill_score_2=weight_score_2,
                    weight_skill_score_3=weight_score_3,
                    weight_off_round_time=weight_off_round_time,
                    soft_rules=frozenset(SOFT_RULE_NAMES))


def _unparsed_settings(sheet: Worksheet) -> dict[str, str]:
    """Every setting on the Settings tab as {name: value}, both as text (through cell_text).

    A row without a name is skipped. Raises WorkbookError for a missing Setting or Value
    column, or a name that appears twice.
    """
    columns = find_columns(sheet, ["Setting", "Value"])

    unparsed_settings = {}
    for row in range(2, sheet.max_row + 1):
        setting_name = cell_text(sheet.cell(row=row, column=columns["Setting"]).value)
        if setting_name == "":
            continue  # an empty row: skip it

        if setting_name in unparsed_settings:
            raise WorkbookError(f"Settings: two settings with name {setting_name!r}.")
        unparsed_settings[setting_name] = cell_text(
            sheet.cell(row=row, column=columns["Value"]).value)

    return unparsed_settings


def _check_setting_names(unparsed_settings: dict[str, str]) -> None:
    """Raise WorkbookError for an unknown setting, or a required one that is missing or empty.

    Unknown = not in KNOWN_SETTINGS (catches typos); required = REQUIRED_SETTINGS.
    """
    for name in unparsed_settings:
        if name not in KNOWN_SETTINGS:
            raise WorkbookError(f"Settings: unknown setting {name!r}")

    for required_setting in REQUIRED_SETTINGS:
        if required_setting not in unparsed_settings:
            raise WorkbookError(f"Settings: Missing required setting {required_setting!r}")
        if unparsed_settings[required_setting] == "":
            raise WorkbookError(f"Settings: the required setting {required_setting!r} is empty.")


def _check_settings_with_one_allowed_value(unparsed_settings: dict[str, str]) -> None:
    """Raise WorkbookError if a setting with only one allowed value for now has another one.

    Workbook format version must be WORKBOOK_FORMAT_VERSION, Time step MINUTES_PER_BLOCK
    (15) and Day boundary DAY_STARTS_AT_HOUR (06:00).
    """
    try:
        version = parse_whole_number("Workbook format version",
                                     unparsed_settings["Workbook format version"], 0)

        time_step = parse_whole_number("Time step", unparsed_settings["Time step"], 0)
    except ValueError as error:
        raise WorkbookError(f"Settings, {error}") from None

    if version != WORKBOOK_FORMAT_VERSION:
        raise WorkbookError(f"Settings, 'Workbook format version': this workbook is version "
                            f"{version}, this scheduler reads version {WORKBOOK_FORMAT_VERSION}.")
    if time_step != MINUTES_PER_BLOCK:
        raise WorkbookError(f"Settings, 'Time step': the scheduler only supports "
                            f"{MINUTES_PER_BLOCK} minutes for now, not {time_step}.")

    # cell_text already turned a time typed into Excel into text, so compare as text.
    day_boundary = unparsed_settings["Day boundary"]
    expected_day_boundary = f"{DAY_STARTS_AT_HOUR:02d}:00"
    if day_boundary != expected_day_boundary:
        raise WorkbookError(f"Settings, 'Day boundary': the scheduler only supports "
                            f"{expected_day_boundary} for now, not {day_boundary}.")


def parse_days(text: str) -> tuple[str, ...]:
    """The Days setting as a tuple: "Friday, Saturday, Sunday" -> ("Friday", "Saturday", ...).

    Raises ValueError for an empty day name ("Friday, , Saturday" or a comma at the end)
    or a day that appears more than once (naming that day); read_settings puts the tab and
    setting in front. Public because it is tested on its own (test_parse_values.py).
    """
    days = []
    for day in text.split(","):
        day = day.strip()
        if day == "":
            raise ValueError("an empty day name (two commas in a row, or a comma at the end).")
        if day in days:
            raise ValueError(f"{day!r} appears more than once.")
        days.append(day)

    return tuple(days)  # a tuple, like the default in Settings


def _optional_whole_number_setting(unparsed_settings: dict[str, str],
                                   name: str, default: int) -> int:
    """An optional whole number setting (at least 0) from the Settings tab,
    e.g. a soft rule weight.
    """
    # A missing row counts the same as an empty Value: both give the default.
    text = unparsed_settings.get(name, "")
    if text == "":
        return default

    return parse_whole_number(name, text, 0)
