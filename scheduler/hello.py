from ortools.sat.python import cp_model

def hello() -> str:
    return "Hello, PonyCon!"


def solver_says_hello() -> tuple[int, int]:
    model = cp_model.CpModel()
    x = model.NewIntVar(0, 10, "x")
    y = model.NewIntVar(0, 10, "y")
    model.Add(x + y == 7)
    model.Add(x > y)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    assert status in (cp_model.OPTIMAL, cp_model.FEASIBLE), "No solution found"
    return solver.Value(x), solver.Value(y)