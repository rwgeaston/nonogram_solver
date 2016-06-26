from collections import defaultdict
import itertools

from nonograms import NonogramGrid, empty, empty_tile, NonogramImpossible


def generate_blocks(values, empty_at_start=0, separator=empty):
    for empty_tile in xrange(empty_at_start):
        yield empty
    for value in values:
        for item in xrange(value):
            yield value
        yield separator


def normal(whatever):
    # for syntactic reasons i want the null function later
    return whatever


# decorator that takes a rule aimed at one row or column and does the whole lot
# most rules will need this
def try_every_row_and_column(rule_function):
    def rule_function_try_every(self):
        for index, row in enumerate(self.rows):
            if not self.completed('row', index) and rule_function(self, index, row, 'row'):
                return "row {}".format(index)
        for index, column in enumerate(self.columns):
            if not self.completed('column', index) and rule_function(self, index, column, 'column'):
                return "column {}".format(index)
        return False
    return rule_function_try_every


class NonogramSolver(NonogramGrid):
    rules = [
        'fill_fully_entire_line', 'fill_middle', 'cross_out_too_far_from_any_block',
        'got_enough_filled_or_not_filled', 'fill_block_if_it_touches_edge',
        'rule_out_values_too_small_for_this_block', 'rule_out_values_based_on_already_used_up',
        'next_to_known_empty', 'remove_options_if_other_pieces_before_it',
        'cross_out_too_far_from_known_value', 'block_long_enough', 'split_row_by_known_block',
        'fill_from_edge', 'too_far_from_known_block_repeated_values', 'eliminate_wrong_side'
    ]

    def try_all_rules(self):
        for rule in self.rules:
            outcome = getattr(self, rule)()
            if outcome:
                return "We made progress using the '{}' rule ({}):".format(rule, outcome)
        return False

    # if the values for one row + the number of values - 1 is equal to the length of the row,
    # you can fill it in fully. crossed out positions at either end can be subtracted from target sum.
    @try_every_row_and_column
    def fill_fully_entire_line(self, index, values, direction):
        tiles = self.get_line(direction, index)
        return self.fill_fully(values, direction, tiles)

    def fill_fully(self, values, direction, tiles):
        empty_at_start, empty_at_end = self.get_empty_count_at_ends(tiles, direction)
        if sum(values) + len(values) - 1 == self.size[direction] - empty_at_start - empty_at_end:
            for tile, value in zip(tiles, generate_blocks(values, empty_at_start)):
                tile.set_only_option(value, direction)
            return True
        else:
            return False

    # entirely superseded by fill_middle
    @try_every_row_and_column
    def long_block_fill_middle(self, index, values, direction):
        # TODO consider not just values more than 1/2 size of entire row,
        # but also more than 1/2 size of biggest remaining free section
        # TODO allow space at either end for other values that have to fit
        # i.e. 1,6 in a 10 has more information than just a 6 in a 10
        # TODO in fact generalise it to fit e.g. 4, 4 in a 10. Can fill a bunch of things from that.
        highest = max(values)
        tiles = self.get_line(direction, index)
        empty_at_start, empty_at_end = self.get_empty_count_at_ends(tiles, direction)
        if highest <= (self.size[direction] - empty_at_start - empty_at_end)/2:
            return False

        # tiles known to be definitely empty at the end mean we have to fill in more tiles at the start
        spaces_to_leave_at_start = self.size[direction] - highest - empty_at_end
        space_to_leave_at_end = self.size[direction] - highest - empty_at_start

        # tiles will tell us if anything changed
        return any([
            tile.set_only_option(highest, direction)
            for tile in self.get_line(direction, index)[spaces_to_leave_at_start:-space_to_leave_at_end]
        ])

    @try_every_row_and_column
    def fill_middle(self, index, values, direction):
        tiles = self.get_line(direction, index)
        changes_made = False
        for value in values:
            changes_made += self.fill_middle_this_value(index, values, direction, value, tiles)
        return changes_made

    def fill_middle_this_value(self, index, values, direction, value, tiles):
        contiguous_spaces_this_value = self.get_contiguous_valid_spaces(value, tiles, direction)
        changes_made = False
        for start, length in contiguous_spaces_this_value:
            if value > length:
                for position in xrange(start, start + length):
                    if value in tiles[position].possible_values[direction]:
                        changes_made = True
                        tiles[position].remove_option(value, direction)

        # TODO think about how to make this work in a row with the same value twice
        # might require a significant rethink of tiles
        if (
            values.count(value) == len(contiguous_spaces_this_value) and
            max((length for start, length in contiguous_spaces_this_value)) < 2 * value + 1
        ):
            for start, length in contiguous_spaces_this_value:
                # Since there is only one place to put this block let's try to place the middle of it
                start_placing = start + length - value
                end_placing = start + value
                for position in xrange(start_placing, end_placing):
                    changes_made += tiles[position].set_only_option(value, direction)
        return changes_made

    def get_contiguous_valid_spaces(self, value, tiles, direction):
        value_allowed_here = False
        spaces = []
        for index, tile in enumerate(tiles + [empty_tile]):
            value_allowed_previous_tile, value_allowed_here = value_allowed_here, value in tile.possible_values[direction]
            if value_allowed_here:
                if value_allowed_previous_tile:
                    length += 1
                else:
                    start = index
                    length = 1
            elif value_allowed_previous_tile:
                spaces.append((start, length))
        return spaces

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

    def get_empty_count_at_ends(self, tiles, direction):
        empty_at_start = 0
        while empty_at_start < len(tiles) and tiles[empty_at_start].decided[direction] and not tiles[empty_at_start].filled:
            empty_at_start += 1
        empty_at_end = 0
        while empty_at_end < len(tiles) and tiles[-empty_at_end-1].decided[direction] and not tiles[-empty_at_end-1].filled:
            empty_at_end += 1
        return empty_at_start, empty_at_end

    # This should be deprecated based on fill_from_edge being strictly better?
    @try_every_row_and_column
    def fill_block_if_it_touches_edge(self, index, values, direction):
        # If the first or last tile is filled, we know the position of the entire first or last block
        tiles = self.get_line(direction, index)
        changes_made = False

        if tiles[0].filled:
            for position in xrange(values[0]):
                changes_made += tiles[position].set_only_option(values[0], direction)
            changes_made += tiles[values[0]].set_only_option(empty)

        if tiles[-1].filled:
            for position in xrange(values[-1]):
                changes_made += tiles[-1-position].set_only_option(values[-1], direction)
            changes_made += tiles[-1-values[-1]].set_only_option(empty)

        return changes_made

    @try_every_row_and_column
    def fill_from_edge(self, index, values, direction):
        # Starting from an edge, as long as the tiles are filled or decided, we can make the filled ones decided.
        tiles = self.get_line(direction, index)
        changes_made = False

        for search_direction in [normal, reversed]:
            values_iterator = itertools.chain(*[[value for _ in xrange(value)] for value in search_direction(values)])
            for tile in search_direction(tiles):
                if not (tile.filled or tile.decided[direction]):
                    # That's as far as we can be certain from this edge
                    break
                if tile.filled:
                    next_value = values_iterator.next()
                    changes_made += tile.set_only_option(next_value, direction)
        return changes_made

    @try_every_row_and_column
    def rule_out_values_too_small_for_this_block(self, index, values, direction):
        tiles = self.get_line(direction, index)
        changes_made = False
        length_contiguous_blocks = self.get_contiguous_lengths(tiles)
        for block_size, tile in zip(length_contiguous_blocks, tiles):
            if block_size > 0:
                for value in values:
                    if value < block_size and value in tile.possible_values[direction]:
                        changes_made = True
                        tile.remove_option(value, direction)
        return changes_made

    def get_contiguous_lengths(self, tiles):
        length_contiguous_blocks = []
        current_contiguous_length = 0
        for tile in tiles:
            if tile.filled:
                current_contiguous_length += 1
            else:
                if current_contiguous_length:
                    length_contiguous_blocks.extend([current_contiguous_length]*current_contiguous_length)
                length_contiguous_blocks.append(0)
                current_contiguous_length = 0
        if current_contiguous_length:
            length_contiguous_blocks.extend([current_contiguous_length] * current_contiguous_length)
        if len(length_contiguous_blocks) != len(tiles):
            raise Exception(
                "You lost some values there this function is dodgy {}, {}"
                .format(length_contiguous_blocks, "".join([str(tile) for tile in tiles]))
            )
        return length_contiguous_blocks

    @try_every_row_and_column
    def rule_out_values_based_on_already_used_up(self, index, values, direction):
        # Is this really an extension of 'got_enough_filled_or_not_filled'?
        tiles = self.get_line(direction, index)
        return self.rule_out_values_based_on_already_used_up_partial(index, values, direction, tiles)

    def rule_out_values_based_on_already_used_up_partial(self, index, values, direction, tiles):
        observed_counts = defaultdict(int)

        for tile in tiles:
            if tile.decided[direction]:
                observed_counts[tile.possible_values[direction][0]] += 1

        max_allowed_counts = defaultdict(int)
        for value in values:
            # this looks a bit funky but it's because we might have two 4 groups therefore need 8 "4" tiles
            max_allowed_counts[value] += value

        used_up = [key for key, value in observed_counts.iteritems() if value == max_allowed_counts[key]]
        if not used_up:
            return False

        changes_made = False
        for tile in tiles:
            if not tile.decided[direction]:
                for value in used_up:
                    if value in tile.possible_values[direction]:
                        changes_made = True
                        tile.remove_option(value, direction)
        return changes_made


    @try_every_row_and_column
    def next_to_known_empty(self, index, values, direction):
        # basically generalisation of 'fill_block_if_it_touches_edge'
        tiles = self.get_line(direction, index)
        changes_made = False

        for search_direction in [normal, reversed]:
            last_tile_was_known_empty = True
            to_fill_count = 0
            fill_with = '-'
            for tile in search_direction(tiles):
                if to_fill_count:
                    if to_fill_count == 1:
                        # last tile to fill is actually the empty one after the block ends
                        changes_made += tile.set_only_option(empty, direction)
                        last_tile_was_known_empty = True
                    else:
                        changes_made += tile.set_only_option(fill_with, direction)
                    to_fill_count -= 1
                    continue

                if last_tile_was_known_empty and tile.filled and tile.decided[direction]:
                    fill_with = to_fill_count = tile.possible_values[direction][0]

                if not tile.filled and tile.decided[direction]:
                    last_tile_was_known_empty = True
                else:
                    last_tile_was_known_empty = False

                should_fill = 0
        return changes_made

    @try_every_row_and_column
    def remove_options_if_other_pieces_before_it(self, index, values, direction):
        tiles = self.get_line(direction, index)
        changes_made = False

        for value in values:
            if values.count(value) == 1:
                changes_made += self.remove_options_if_other_pieces_one_value(index, values, direction, value, tiles)
        return changes_made

    def remove_options_if_other_pieces_one_value(self, index, values, direction, value, tiles):
        changes_made = False
        values_before = values[:values.index(value)]
        values_after = values[values.index(value) + 1:]
        minimum_space_before = sum(values_before) + len(values_before)
        minimum_space_after = sum(values_after) + len(values_after)
        for position in xrange(minimum_space_before):
            if value in tiles[position].possible_values[direction]:
                changes_made = True
                tiles[position].remove_option(value, direction)
                #print "{} {} {} can't fit in {}".format(direction, index, value, position)

        for position in xrange(minimum_space_after):
            if value in tiles[-1-position].possible_values[direction]:
                changes_made = True
                tiles[-1-position].remove_option(value, direction)
                #print "{} {} {} can't fit in {}".format(direction, index, value, -1-position)

        return changes_made

    @try_every_row_and_column
    def cross_out_too_far_from_known_value(self, index, values, direction):
        tiles = self.get_line(direction, index)
        changes_made = False

        for position, tile in enumerate(tiles):
            if tile.filled and tile.decided[direction]:
                value = tile.possible_values[direction][0]
                if values.count(value) == 1:
                    changes_made += self.try_to_remove_far_away_tiles_from_known_value(
                        tiles, direction, position, tile, value
                    )
        return changes_made

    def try_to_remove_far_away_tiles_from_known_value(self, tiles, direction, position, tile, value):
        changes_made = False

        for position_to_change, tile_might_change in enumerate(tiles):
            if abs(position - position_to_change) >= value and value in tile_might_change.possible_values[direction]:
                changes_made = True
                tile_might_change.remove_option(value, direction)
        return changes_made

    def get_known_blocks(self, index, values, direction):
        tiles = self.get_line(direction, index)
        last_tile_filled = False
        value_this_block = 'unknown'
        blocks = []
        for position, tile in enumerate(tiles + [empty_tile]):
            if tile.filled:
                if last_tile_filled:
                    length_contiguous += 1
                else:
                    start_contiguous = position
                    length_contiguous = 1
                if tile.decided[direction]:
                    value_this_block = tile.possible_values[direction][0]
                last_tile_filled = True
            else:
                if value_this_block != 'unknown':
                    blocks.append((start_contiguous, length_contiguous, value_this_block))
                    value_this_block = 'unknown'
                last_tile_filled = False
        return blocks

    @try_every_row_and_column
    def block_long_enough(self, index, values, direction):
        tiles = self.get_line(direction, index)
        changes_made = False
        blocks = self.get_known_blocks(index, values, direction)
        for start, length, value in blocks:
            if value == length:
                # we've found the whole thing so let's put empties either end
                after = start + length
                if after < self.size[direction]:
                    changes_made += tiles[after].set_only_option(empty)
                if start > 0:
                    changes_made += tiles[start - 1].set_only_option(empty)
                    for tile_to_check in tiles[start:start+length]:
                        changes_made += tile_to_check.set_only_option(value, direction)
        return changes_made

    @try_every_row_and_column
    def split_row_by_known_block(self, index, values, direction):
        tiles = self.get_line(direction, index)
        changes_made = False
        blocks = self.get_known_blocks(index, values, direction)

        for start, length, value in blocks:
            if values.count(value) == 1:
                where_split = values.index(value)
                # Definitely know which other blocks have to be before and after this
                values_before = values[:where_split]
                values_after = values[where_split+1:]
                tiles_before = tiles[:start]
                tiles_after = tiles[start+length:]
                changes_made += self.fill_fully(values_before, direction, tiles_before)
                changes_made += self.fill_fully(values_after, direction, tiles_after)
                changes_made += self.rule_out_values_based_on_already_used_up_partial(
                    index, values_before, direction, tiles_before
                )
                changes_made += self.rule_out_values_based_on_already_used_up_partial(
                    index, values_after, direction, tiles_after
                )
        return changes_made

    @try_every_row_and_column
    def too_far_from_known_block_repeated_values(self, index, values, direction):
        tiles = self.get_line(direction, index)
        changes_made = False
        known_by_value = defaultdict(list)

        for position, tile in enumerate(tiles):
            if tile.filled and tile.decided[direction]:
                known_by_value[tile.possible_values[direction][0]].append(position)

        for value in set(values):
            if values.count(value) == 1:
                # other rules take care of this pretty well
                pass
            elif values.count(value) > 2:
                # TODO harder than the twice repeated case
                pass
            else:
                # appears exactly twice
                relevant_positions = known_by_value[value]
                relevant_positions.sort()
                if len(relevant_positions) < 2:
                    continue
                lowest = relevant_positions[0]
                highest = relevant_positions[-1]
                if relevant_positions[-1] - relevant_positions[0] >= value:
                    # we know both instances of this value are implicitly (partially) placed
                    in_left = [lowest]
                    in_right = [highest]
                    for position in relevant_positions[1:-1]:
                        if position - lowest >= value and highest - position >= value:
                            raise NonogramImpossible(
                                "The blocks with value {} are {} (and maybe others) which makes no sense"
                                .format(value, relevant_positions)
                            )
                        elif position - lowest < value and highest - position < value:
                            # don't know which block this is in of the two
                            continue
                        elif position - lowest < value:
                            in_left.append(position)
                        elif highest - position < value:
                            in_right.append(position)
                        else:
                            raise Exception("Some fishy logic going on here")

                    in_left.sort()
                    in_right.sort()

                    if direction == 'row' and index == 13:
                        print in_left
                        print in_right

                    for positions in [in_left, in_right]:
                        if len(positions) > value:
                            raise Exception("some fishy logic going on here")
                        if len(positions) < positions[-1] - positions[0]:
                            # Some values are missing from this list
                            changes_made = True
                            for position in xrange(positions[0], positions[-1]):
                                tiles[position].set_only_option(value, direction)

                    for position, tile in enumerate(tiles):
                        if (
                            (abs(position - in_left[0]) >= value or abs(position - in_left[-1]) >= value) and
                            (abs(position - in_right[0]) >= value or abs(position - in_right[-1]) >= value)
                        ):
                            # it can't be in either group
                            if value in tile.possible_values[direction]:
                                tile.remove_option(value, direction)
                                changes_made = True
        return changes_made

    @try_every_row_and_column
    def speculative_place_end_of_row(self, index, value, direction):
        # not convinced this has a lot of value
        # however we can sometimes reach otherwise hard to spot contradictions by speculatively putting something
        # at the end of a row and reaching a contradiction
        # at which point we know that end of row slot is definitely unfilled
        pass

    # TODO some improvement when filling in from the start or end. currently stop at the first empty tile but
    # other known not filled tiles in the row might rule out that as well

    @try_every_row_and_column
    def eliminate_wrong_side(self, index, values, direction):
        tiles = self.get_line(direction, index)
        changes_made = False
        unique_values = set(values)

        fixed_points_by_value = defaultdict(list)

        for position, tile in enumerate(tiles):
            if tile.filled and tile.decided[direction]:
                # Then we have a fixed point to use
                fixed_points_by_value[tile.possible_values[direction][0]].append(position)

        for value, fixed_points in fixed_points_by_value.iteritems():
            fixed_points.sort()
            first_appearance = values.index(value)
            # why is there no rindex !?
            last_appearance = first_appearance
            for position, possible_match in enumerate(values):
                if possible_match == value:
                    last_appearance = position

            for eliminate in unique_values:
                if value == eliminate:
                    continue
                if eliminate not in values[first_appearance:]:
                    # This value does not appear after the fixed point value
                    # so remove it as an option from all those tiles
                    for tile in tiles[fixed_points[0]:]:
                        if eliminate in tile.possible_values[direction]:
                            changes_made = True
                            tile.remove_option(eliminate, direction)

                if eliminate not in values[:last_appearance]:
                    # This value does not appear before the fixed point value
                    # so remove it as an option from all those tiles
                    for tile in tiles[:fixed_points[-1]]:
                        if eliminate in tile.possible_values[direction]:
                            changes_made = True
                            tile.remove_option(eliminate, direction)

        return changes_made
