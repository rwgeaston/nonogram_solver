import os
from pprint import pprint
from collections import defaultdict

from nonograms import nonograms_input_reader, empty
from tally_nonogram_rules import tally_nonogram_rules_used

local_folder = os.path.dirname(os.path.realpath(__file__))
data = nonograms_input_reader(os.path.join(local_folder, "nonograms_data6.txt"))
rows_sum = sum((sum(row) for row in data['rows']))
columns_sum = sum((sum(column) for column in data['columns']))
if rows_sum != columns_sum:
    print len(data['rows']), rows_sum
    print len(data['columns']), columns_sum
    raise Exception("This doesn't add up")

tallies = defaultdict(int)
for i in range(20):
    solver, tallies = tally_nonogram_rules_used(data['rows'], data['columns'], tallies)

    print unicode(solver)
    pprint(dict(tallies))
