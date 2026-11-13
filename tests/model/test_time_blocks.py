import pytest

from scheduler.model import Settings, all_blocks, block_of, day_and_time_of, day_of


def test_first_day_at_six_is_block_0():
    """06:00 on the first convention day is block 0."""
    # Arrange
    settings = Settings()

    # Act
    block = block_of("Friday", "06:00", settings)

    # Assert
    assert block == 0


def test_daytime_is_counted_in_blocks_from_six():
    """13:30 is 7.5 hours after 06:00, so 30 blocks of 15 minutes."""
    # Arrange
    settings = Settings()

    # Act
    block = block_of("Friday", "13:30", settings)

    # Assert
    assert block == 30


def test_second_day_at_six_is_block_96():
    """06:00 on the second day comes right after the 96 blocks of the first day."""
    # Arrange
    settings = Settings()

    # Act
    block = block_of("Saturday", "06:00", settings)

    # Assert
    assert block == 96


def test_night_time_belongs_to_the_previous_day():
    """Saturday 01:00 is the Saturday night: 96 + 19 hours after 06:00 = 172."""
    # Arrange
    settings = Settings()

    # Act
    block = block_of("Saturday", "01:00", settings)

    # Assert
    assert block == 172


def test_days_come_from_the_settings():
    """With days starting on Saturday, Saturday 06:00 is block 0."""
    # Arrange
    settings = Settings(days=("Saturday", "Sunday"))

    # Act
    block = block_of("Saturday", "06:00", settings)

    # Assert
    assert block == 0


def test_day_and_time_of_turns_a_block_back_into_day_and_time():
    """Block 30 is Friday 13:30."""
    # Arrange
    settings = Settings()

    # Act
    day_and_time = day_and_time_of(30, settings)

    # Assert
    assert day_and_time == ("Friday", "13:30")


def test_day_and_time_of_shows_night_blocks_under_the_previous_day():
    """Block 172 is shown as Saturday 01:00, not Sunday 01:00."""
    # Arrange
    settings = Settings()

    # Act
    day_and_time = day_and_time_of(172, settings)

    # Assert
    assert day_and_time == ("Saturday", "01:00")


def test_day_of_gives_the_convention_day_of_a_block():
    """Block 172 (Saturday night 01:00) belongs to Saturday."""
    # Arrange
    settings = Settings()

    # Act
    day = day_of(172, settings)

    # Assert
    assert day == "Saturday"


def test_unknown_day_raises_value_error():
    """A day that is not in the settings gives a clear error."""
    # Arrange
    settings = Settings()

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while block_of runs.)

    # Assert
    with pytest.raises(ValueError):
        block_of("Monday", "10:00", settings)


# parametrize runs this test once for every time in the list; pytest reports each one
# as its own test, named after the text in ids (e.g. "...[hour too high]").
@pytest.mark.parametrize(
    "invalid_time",
    ["25:00", "24:00", "-1:00", "13:75", "13:60", "12:11", "1330", "12:30:00", "ab:cd", ""],
    ids=["hour too high", "hour 24", "negative hour", "minutes too high", "minutes 60",
         "not on a 15 min step", "no colon", "two colons", "not numbers", "empty"])
def test_invalid_time_raises_value_error(invalid_time):
    """A time that is not a valid HH:MM on a 15-minute step gives a clear error."""
    # Arrange
    settings = Settings()

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while block_of runs.)

    # Assert
    with pytest.raises(ValueError):
        block_of("Friday", invalid_time, settings)


# With the default three days, blocks 0-287 exist. -1 would silently become the last day
# (Python's days[-1]); 288 is the first block after Sunday.
@pytest.mark.parametrize("block", [-1, 288], ids=["before the first day", "after the last day"])
def test_day_of_a_block_outside_the_convention_days_raises_value_error(block):
    """A block before the first day or after the last day gives a clear error."""
    # Arrange
    settings = Settings()

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while day_of runs.)

    # Assert
    with pytest.raises(ValueError):
        day_of(block, settings)


@pytest.mark.parametrize("block", [-1, 288], ids=["before the first day", "after the last day"])
def test_day_and_time_of_a_block_outside_the_convention_days_raises_value_error(block):
    """A block before the first day or after the last day gives a clear error."""
    # Arrange
    settings = Settings()

    # Act
    # (Act and Assert are combined, pytest.raises checks the exception while day_and_time_of runs.)

    # Assert
    with pytest.raises(ValueError):
        day_and_time_of(block, settings)


def test_all_blocks_covers_every_block_of_every_convention_day():
    """Three convention days of 96 blocks each give blocks 0 up to 287."""
    # Arrange
    settings = Settings(days=("Friday", "Saturday", "Sunday"))

    # Act
    blocks = all_blocks(settings)

    # Assert
    assert blocks == set(range(288))


def test_all_blocks_follows_the_days_in_the_settings():
    """With only Saturday and Sunday, there are 2 * 96 blocks: 0 up to 191."""
    # Arrange
    settings = Settings(days=("Saturday", "Sunday"))

    # Act
    blocks = all_blocks(settings)

    # Assert
    assert blocks == set(range(192))
