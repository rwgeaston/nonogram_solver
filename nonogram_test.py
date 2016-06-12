import os

from nonograms import nonograms_input_reader
from nonogram_solver import NonogramSolver

local_folder = os.path.dirname(os.path.realpath(__file__))
data = nonograms_input_reader(os.path.join(local_folder, "nonograms_data2.txt"))
print data
solver = NonogramSolver(data['rows'], data['columns'])
print solver.grid
while solver.try_all_rules():
    print solver.grid