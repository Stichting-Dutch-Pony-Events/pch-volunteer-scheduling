"""Solving: from a Problem to a Schedule.

    solver.py           solve(): checks the problem, builds the CP-SAT model and solves it
    checks.py           quick checks before solving (check_problem) and warnings about
                        likely mistakes in the input (find_warnings)
    variables.py        the solver's yes/no variables and helpers to find them again
    hard_rules.py       the hard rules, one add_<name>_rule() function each
"""
