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
        for index, row in enumerate(self.rows):
            if not self.completed('row', index) and rule_function(self, index, row, 'row'):
                return True
        for index, column in enumerate(self.columns):
            if not self.completed('column', index) and rule_function(self, index, column, 'column'):
                return True
        return False
    return rule_function_try_every


class NonogramSolver(NonogramGrid):
    rules = ['fill_fully', 'long_block_fill_middle']

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
        # TODO discount already eliminated tiles at the start and end
        if sum(values) + len(values) - 1 == self.size[direction]:
            for tile, value in zip(self.get_line(direction, index), generate_blocks(values)):
                tile.set_only_option(value, direction)
            return True
        else:
            return False

    @try_every_row_and_column
    def long_block_fill_middle(self, index, values, direction):
        # TODO consider not just values more than 1/2 size of entire row,
        # but also more than 1/2 size of biggest remaining free section
        # TODO allow space at either end for other values that have to fit
        # i.e. 1,6 in a 10 has more information than just a 6 in a 10
        highest = max(values)
        if highest <= self.size[direction]/2:
            return False

        spaces_to_leave_either_end = self.size[direction] - highest
        # tiles will tell us if anything changed
        return any([
            tile.set_only_option(highest, direction)
            for tile in self.get_line(direction, index)[spaces_to_leave_either_end:-spaces_to_leave_either_end]
        ])



