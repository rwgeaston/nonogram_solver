#-*-coding:utf8;-*-
from copy import copy


class NonogramImpossible(Exception):
    pass


class NonogramBadRequest(Exception):
    pass


class NonogramGrid(list):
    def __init__(self, row_values, column_values):
        super(NonogramGrid, self).__init__()
        self.columns = column_values
        self.rows = row_values
        self.max_column_options = max((len(values) for values in column_values))
        self.max_row_options = max((len(values) for values in row_values))
        self.enforce_inputs()
        for i, row in enumerate(row_values):
            self.append([NonogramTile(j, i, column, row) for j, column in enumerate(column_values)])
        # self[x] is the xth row i.e. the vertical coord
        # self[x][y] is the yth element of xth row i.e. y is horizontal component
        # but I want to access them by name because I always get confused otherwise

    def enforce_inputs(self):
        assert isinstance(self.rows, list)
        assert isinstance(self.columns, list)
        assert all(isinstance(row, list) for row in self.rows)
        assert all(isinstance(column, list) for column in self.columns)

    def get_value(self, column, row):
        return self[column][row]

    def get_row(self, vert):
        return self[vert]

    def get_column(self, horiz):
        return [row[horiz] for row in self]

    def __str__(self):
        rows = []
        for negative_row in range(-self.max_column_options, 0):
            row = []
            for column in self.columns:
                try:
                    next_value = column[negative_row]
                except IndexError:
                    next_value = ' '
                row.append(str(next_value))
            rows.append(' ' * (self.max_row_options*2 + 1) + ' '.join(row))

        rows.append(' ' * (self.max_row_options*2 + 1) + '_' * (len(self.columns)*2 - 1))
        for row_input_values, row_current_values in zip(self.rows, self):
            row_string = '{}{} |{}'.format(
                ' ' * (self.max_row_options - len(row_input_values)) * 2,
                ','.join([str(value) for value in row_input_values]),
                ' '.join([str(tile) for tile in row_current_values])
            )
            rows.append(row_string)
        return '\n'.join(rows)

empty = 'x'


class NonogramTile(object):
    # Each tile in the grid remembers what possible values it could still be (after being initialised)
    def __init__(self, column, row, possible_values_column, possible_values_row):
        self.column = column
        self.row = row
        self.possible_values = {
            'row': copy(possible_values_row),
            'column': copy(possible_values_column)
        }
        for options in self.possible_values.itervalues():
            options.append(empty)

        # tracks if we know what block this tile is part of or know it's definitely not filled
        self.decided = {direction: False for direction in self.possible_values}
        self.filled = False  # tracks if this tile is definitely filled (might not know what block it's part of)
        #print "creating: {}".format(repr(self))

    def check_if_decided(self):
        possibilities_left = len(self.possible_values)
        if possibilities_left == 0:
            raise NonogramImpossible("Tile {} can't take any values".format(self))
        elif possibilities_left == 1:
            self.decided = True

    def remove_option(self, value, direction=None):
        if value == empty:
            if any((empty not in values for values in self.possible_values.itervalues())):
                raise NonogramBadRequest("Tile {} has got itself into a contradictory state".format(repr(self)))
            for values in self.possible_values.itervalues():
                values.remove(empty)
        elif not direction:
            raise NonogramBadRequest(
                "You can't remove an value from a tile without saying which direction it's not valid in"
            )
        elif direction in self.possible_values:
            if value not in self.possible_values['direction']:
                raise NonogramBadRequest(
                    "Can't remove {} from {} {}-wise"
                    .format(value, repr(self), direction)
                )
            self.possible_values[direction].remove(value)
        else:
            raise NonogramBadRequest(
                "Can't work out what to do with these inputs {} {} in tile {}"
                .format(value, direction, repr(self))
            )
        self.check_if_decided()

    def __repr__(self):
        return (
            "<Nonogram tile coords:{},{} filled:{} decided:{} possible:{}>"
            .format(self.column, self.row, self.filled, self.decided, self.possible_values)
        )

    def __str__(self):
        #return str((self.column, self.row))
        if self.filled:
            return u'█'
        elif any(self.decided.itervalues()):
            # decided not filled means proven empty
            return 'x'
        else:
            return '.'


def nonograms_input_reader(filename):
    with open(filename) as handler:
        lines = handler.readlines()
    inputs = {'rows': [], 'columns': []}
    for line in lines:
        line = line.strip()
        if line in inputs:
            next_input = line
        else:
            inputs[next_input].append([int(value) for value in line.split(',')])
    return inputs