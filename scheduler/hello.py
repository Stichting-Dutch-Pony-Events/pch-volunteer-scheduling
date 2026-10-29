from ortools.sat.python import cp_model

def hello() -> str:
    return "Hello, PonyCon!"


def solver_says_hello() -> tuple[int, int]:
    model = cp_model.CpModel()
    x = model.new_int_var(0, 10, "x")
    y = model.new_int_var(0, 10, "y")
    model.add(x + y == 7)
    model.add(x > y)

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE), "No solution found"
    return solver.value(x), solver.value(y)