from nonograms import NonogramGrid, empty


def generate_blocks(values, separator=empty):
    for value in values:
        for item in xrange(value):
            yield value
        yield separator


# decorator that takes a rule aimed at one row or column and does the whole lot
# most rules will need this
def try_every_row_and_column(rule_function):
    def rule_function_try_every(self):
        for index, row in enumerate(self.grid.rows):
            if rule_function(self, index, row, 'row'):
                return True
        for index, column in enumerate(self.grid.columns):
            if rule_function(self, index, column, 'column'):
                return True
        return False
    return rule_function_try_every


class NonogramSolver(object):
    def __init__(self, row_values, column_values):
        self.grid = NonogramGrid(row_values, column_values)

    rules = ['fill_fully']

    def try_all_rules(self):
        for rule in self.rules:
            if getattr(self, rule)():
                print "We made progress using the '{}' rule".format(rule)
                return True
        return False

    # if the values for one row + the number of values - 1 is equal to the length of the row,
    # you can fill it in fully. crossed out positions at either end can be subtracted from target sum.
    @try_every_row_and_column
    def fill_fully(self, index, values, direction):
        if self.grid.completed(direction, index):
            return False
        if sum(values) + len(values) - 1 == self.grid.size[direction]:
            for tile, value in zip(self.grid.get_line(direction, index), generate_blocks(values)):
                tile.set_only_option(value, direction)
            return True
        else:
            return False
