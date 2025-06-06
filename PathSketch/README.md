# PathSketch
No hassle, No pip install, Just Copy Paste the code and run
## Basic usage
python tree.py

## Show all files with sizes, limit depth to 3
python tree.py -a -s -L 3

## Only Python files, sorted by size
python tree.py -P "*.py" --sort size

## Ignore log files, save to file
python tree.py --ignore "*.log" -o tree.txt

## ASCII style without colors
python tree.py --style ascii --no-color