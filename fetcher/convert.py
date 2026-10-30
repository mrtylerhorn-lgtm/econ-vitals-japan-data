"""Econ Vitals Japan: turn downloaded .xls files into JSON (one list of rows per sheet).

Usage:  python3 convert.py RAWDIR      (needs xlrd; the GitHub Action installs it)
Each RAWDIR/<src>/<name>.xls becomes RAWDIR/<src>/<name>.json and the .xls is removed.
"""
import json, os, sys, glob
import xlrd
for path in glob.glob(os.path.join(sys.argv[1], '*', '*.xls')):
    wb = xlrd.open_workbook(path)
    out = {}
    for sh in wb.sheets():
        out[sh.name] = [[c.value if c.ctype != xlrd.XL_CELL_EMPTY else None for c in sh.row(r)] for r in range(sh.nrows)]
    json.dump(out, open(path[:-4] + '.json', 'w'), ensure_ascii=False)
    os.remove(path)
    print('converted', path, {k: len(v) for k, v in out.items()})
