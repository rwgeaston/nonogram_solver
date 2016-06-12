import nonograms

data = nonograms.nonograms_input_reader("C:/Users/Robert Easton/Documents/Scripts/nonograms/nonograms_data.txt")
print data
grid = nonograms.NonogramGrid(data['rows'], data['columns'])
print grid
