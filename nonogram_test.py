import os

from nonograms import nonograms_input_reader
from nonogram_solver import NonogramSolver

local_folder = os.path.dirname(os.path.realpath(__file__))
data = nonograms_input_reader(os.path.join(local_folder, "nonograms_data4.txt"))
solver = NonogramSolver(data['rows'], data['columns'])
print unicode(solver)

while True:
    outcome = solver.try_all_rules()
    if not outcome:
        break
    print outcome
    #print solver.__unicode__('row')
    #print solver.__unicode__('column')

print "final grid:"
print unicode(solver)
