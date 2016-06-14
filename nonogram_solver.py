from nonograms import NonogramGrid, empty


def generate_blocks(values, empty_at_start=0, separator=empty):
    for empty_tile in xrange(empty_at_start):
        yield empty
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
    rules = ['fill_fully', 'long_block_fill_middle', 'cross_out_too_far_from_any_block', 'got_enough_filled_or_not_filled']

    def try_all_rules(self):
        for rule in self.rules:
            if getattr(self, rule)():
                print "We made progress using the '{}' rule:".format(rule)
                return True
        return False

    # if the values for one row + the number of values - 1 is equal to the length of the row,
    # you can fill it in fully. crossed out positions at either end can be subtracted from target sum.
    @try_every_row_and_column
    def fill_fully(self, index, values, direction):
        # TODO discount already eliminated tiles at the start and end
        tiles = self.get_line(direction, index)
        empty_at_start = 0
        while tiles[empty_at_start].decided[direction] and not tiles[empty_at_start].filled:
            empty_at_start += 1
        empty_at_end = 0
        while tiles[-empty_at_end-1].decided[direction] and not tiles[-empty_at_end-1].filled:
            empty_at_end += 1
        if sum(values) + len(values) - 1 == self.size[direction] - empty_at_start - empty_at_end:
            for tile, value in zip(self.get_line(direction, index), generate_blocks(values, empty_at_start)):
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
        # TODO in fact generalise it to fit e.g. 4, 4 in a 10. Can fill a bunch of things from that.
        highest = max(values)
        if highest <= self.size[direction]/2:
            return False

        spaces_to_leave_either_end = self.size[direction] - highest
        # tiles will tell us if anything changed
        return any([
            tile.set_only_option(highest, direction)
            for tile in self.get_line(direction, index)[spaces_to_leave_either_end:-spaces_to_leave_either_end]
        ])

    @try_every_row_and_column
    def cross_out_too_far_from_any_block(self, index, values, direction):
        tiles = self.get_line(direction, index)
        # TODO if all blocks are implicitly placed, fill in any gaps you can.
        # e.g. a row has 2, 2 with a big gap in the middle
        anything_changed = False
        if len(values) == 1 and any((tile.filled for tile in tiles)):
            # so we might be able to cross out values too far from the other end of the block
            block_length = values[0]
            filled_indices = [index for index, tile in enumerate(tiles) if tile.filled]
            first = min(filled_indices)
            last = max(filled_indices)
            if last - first >= block_length:
                raise Exception(
                    "Something fishy in {} {} because the start and end of the only block is {} apart"
                    .format(direction, index, last - first)
                )
            for index, tile in enumerate(tiles):
                if index <= last - block_length or index >= first + block_length:
                    anything_changed += tile.set_only_option(empty)
                if first <= index <= last:
                    anything_changed += tile.set_only_option(block_length, direction)
        return anything_changed

    @try_every_row_and_column
    def got_enough_filled_or_not_filled(self, index, values, direction):
        tiles = self.get_line(direction, index)
        tiles_need_filled_in = sum(values)
        tiles_need_not_filled = len(tiles) - tiles_need_filled_in
        tiles_filled = []
        tiles_definitely_empty = []
        tiles_unknown = []
        for tile in tiles:
            if tile.decided[direction]:
                if tile.filled:
                    tiles_filled.append(tile)
                else:
                    tiles_definitely_empty.append(tile)
            elif empty not in tile.possible_values[direction]:
                tiles_filled.append(tile)
            else:
                tiles_unknown.append(tile)
        if len(tiles_filled) > tiles_need_filled_in:
            raise Exception(
                "How can {} {} have more tiles filled than it's supposed to?"
                .format(direction, index)
            )
        elif len(tiles_filled) == tiles_need_filled_in:
            for tile in tiles_unknown:
                tile.set_only_option(empty)
            return bool(tiles_unknown)

        if len(tiles_definitely_empty) > tiles_need_not_filled:
            raise Exception(
                "How can {} {} have more tiles definitely empty than it's supposed to?"
                .format(direction, index)
            )
        elif len(tiles_definitely_empty) == tiles_need_not_filled:
            position_to_fill = 0
            for value in values:
                for within_block_num in xrange(value):
                    while tiles[position_to_fill] in tiles_definitely_empty:
                        position_to_fill += 1
                    tiles[position_to_fill].set_only_option(value, direction)
                    position_to_fill += 1
            return True
        return False
