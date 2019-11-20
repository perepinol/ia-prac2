#!/bin/python

import os
import sys
import wcnf
import msat_runner

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Use: python 13cnftester.py <solver> <cnf dir>")
    solver = sys.argv[1]
    dir = sys.argv[2]
    instances = os.listdir(dir)
    for file in instances:
        wpm = wcnf.load_from_file(dir + "/" + file)
        wpm13 = wpm.to_13wpm()

        wpm_sol = msat_runner.solve_formula(solver, wpm)
        wpm13_sol = msat_runner.solve_formula(solver, wpm13)

        error = ""
        if (wpm_sol[0] != wpm13_sol[0]):
            error = "********Different costs*********"
        print("%s %s" % (file, error))
