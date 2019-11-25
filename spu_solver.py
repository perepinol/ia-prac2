#!/usr/bin/env python3
# -*- coding: utf -*-

# pylint: disable=missing-docstring
import argparse


def parse_cmd_args(argv=None):
    """Parse cmd input."""
    parser = argparse.ArgumentParser()
    parser.add_argument("solver", help="Path to the MaxSAT solver.")
    parser.add_argument("problem", help="Instance of the SPU problem.")
    return parser.parse_args(argv)


def is_int(string):
    """Check if a string contains an integer."""
    try:
        int(string)
    except ValueError:
        return False
    return True


def reverse_find(map, value):
    """Find the key that matches the given value in the given map."""
    for k, v in map.items():
        if v == value:
            return k
    raise KeyError


class SPU():
    """Represents an SPU problem as described in the lectures."""

    valid_format = {
        "p": lambda l: len(l) == 3 and l[1] == "spu" and is_int(l[2]),
        "n": lambda l: len(l) == 2,
        "d": lambda l: len(l) >= 3,
        "c": lambda l: len(l) == 3
    }

    class ValidationException(Exception):
        """Represents an error when validating the SPU."""

        pass

    def __init__(self, package_names, dependencies, conflicts):
        """Create an instance of an SPU problem."""
        self.packages = package_names
        self.dep = dependencies
        self.con = conflicts
        self.mapping = {}

    @staticmethod
    def validate_and_parse_SPU(filename):
        """Validate a file containing an SPU and create an instance."""
        # Structure for storage of each type of line
        lines = {"p": [], "n": [], "d": [], "c": []}

        with open(filename) as fh:
            for line in fh:
                line = line.strip()
                parts = line.split()
                # Check that line meets requirements based on initial letter
                if parts[0] not in SPU.valid_format or \
                        not SPU.valid_format[parts[0]](parts):
                    raise SPU.ValidationException(
                        "Invalid format in '%s'" % line
                    )
                # Add line to collection
                lines[parts[0]].append(parts[1:])

        if (len(lines["p"]) != 1):  # There is only one 'p' line
            raise SPU.ValidationException("Invalid number of 'p' lines")

        numvars = int(lines["p"][0][1])
        # There are as many 'n' lines as variables (packages)
        if (len(lines["n"]) != numvars):
            raise SPU.ValidationException(
                "Mismach between number of packages and 'n' lines"
            )

        all_packages = [package[0] for package in lines["n"]]
        # All packages in 'd' and 'c' lines are in 'n' lines
        for line in lines["d"] + lines["c"]:
            for package in line:
                if package not in all_packages:
                    raise SPU.ValidationException(
                        "%s not declared in 'n' lines" % package
                    )

        return SPU(all_packages, lines["d"], lines["c"])

    def solve(self, solver):
        """Solve the SPU and return the solution."""
        import msat_runner
        # Format as WCNF and run solver
        solution = msat_runner.solve_formula(solver, self._as_WCNF())

        # Interpret results
        not_sat = filter(lambda p: p < 0, solution[1])
        not_installed = list(map(
            lambda p: reverse_find(self.mapping, -1 * p),
            not_sat
        ))

        # Format and return
        not_installed.sort()
        return "o %d\nv %s" % (solution[0], " ".join(not_installed))

    def _as_WCNF(self):
        """
        Return the SPU as WCNF.

        The function returns the WCNF instance and the variable mapping.
        """
        import wcnf
        formula = wcnf.WCNFFormula()

        # Add as many variables as packages
        for package in self.packages:
            self.mapping[package] = formula.new_var()

        # Add packages as soft
        for var in self.mapping.values():
            formula.add_clause([var], 1)

        # Add dependencies as hard
        for dep in self.dep:
            c = [self.mapping[dep[0]] * -1] + \
                [self.mapping[predicate] for predicate in dep[1:]]
            formula.add_clause(c, 0)

        # Add conflicts as hard
        for con in self.con:
            con1, con2 = self.mapping[con[0]], self.mapping[con[1]]
            formula.add_clauses([[con1, con2], [-con1, -con2]])

        return formula


if __name__ == "__main__":
    args = parse_cmd_args()
    problem = SPU.validate_and_parse_SPU(args.problem)
    print(problem.solve(args.solver))
