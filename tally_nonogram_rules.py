from collections import defaultdict
from nonogram_solver import NonogramSolver
from random import shuffle

def tally_nonogram_rules_used(rows, columns, tally=None):
    if not tally:
        tally = defaultdict(int)

    solver = NonogramSolver(rows, columns)
    print unicode(solver)
    while True:
        shuffle(solver.rules)
        try:
            outcome = solver.try_all_rules()
        except:
            print unicode(solver)
            raise
        if not outcome:
            break

        rule_applied = outcome.split("'")[1]
        tally[rule_applied] += 1
    return solver, tally
