from scheduler.hello import hello, solver_says_hello


def test_hello():
    """hello() returns the greeting text."""
    # Arrange
    # (nothing to set up: hello() takes no input)

    # Act
    greeting = hello()

    # Assert
    assert greeting == "Hello, PonyCon!"


def test_solver_says_hello():
    """The solver finds x and y with x + y == 7 and x > y."""
    # Arrange
    # (the puzzle is built inside solver_says_hello())

    # Act
    x, y = solver_says_hello()

    # Assert
    assert x + y == 7
    assert x > y
