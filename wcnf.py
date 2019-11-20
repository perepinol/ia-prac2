#!/usr/bin/env python3
# -*- coding: utf -*-

# pylint: disable=missing-docstring

from __future__ import absolute_import, print_function

import io
import itertools
import sys


TOP_WEIGHT = 0


class WCNFException(Exception):
    """Invalid MaxSAT operation."""


class WCNFFormula(object):
    """Represents a formula in "eighted Conjunctive Normal Form."""

    def __init__(self):
        """Construct WCNFFormula."""
        self.num_vars = 0
        self.hard = []  # Item format: [literals]
        self.soft = []  # Item format: (weight, [literals])
        self._sum_soft_weights = 0
        self.header = []

    @property
    def num_clauses(self):
        """Calculate the number of clauses in the formula (soft + hard)."""
        return len(self.hard) + len(self.soft)

    @property
    def top_weight(self):
        """Calculate the formula's top weight."""
        return self._sum_soft_weights + 1

    def clean(self):
        """Reset the formula."""
        self.__init__()

    def add_clauses(self, clauses, weight=TOP_WEIGHT):
        """Add the given set of clauses, having each one the specified weight.

        :param clauses: Iterable filled with sets of literals.
        :type clauses: list[list[int]]
        :param weight: Weight applied to all the clauses, as in add_clause().
        :type weight: int
        """
        for clause in clauses:
            self.add_clause(clause, weight)

    def add_clause(self, literals, weight):
        """Add the given literals as a new clause with the specified weight.

        :param literals: Clause literals
        :type literals: list[int]
        :param weight: Clause weight, less than 1 means infinity.
        :type weight: int
        """
        self._check_literals(literals)
        self._add_clause(literals, weight)

    def extend_vars(self, how_many):
        """Extend the number of used variables."""
        if how_many < 0:
            raise ValueError("Cannot be extended a negative quantity")
        self.num_vars += how_many

    def new_var(self):
        """Return the next free variable of this formula.

        :return: The next free variable (>1).
        :rtype: int
        """
        self.num_vars += 1
        return self.num_vars

    def is_13wpm(self, strict=False):
        """Test if the formula is in 1,3-WPM format."""
        soft_ok = all(len(c) == 1 for _, c in self.soft)
        hard_ok = all(len(c) == 3 or len(c) < 3 and not strict
                      for c in self.hard)
        return soft_ok and hard_ok

    def to_13wpm(self):
        """
        Generate new formula that is the 1,3-WPM equivalent of this one.

        First, an intermediate formula with soft clauses of length 1 and
        hard clauses of any length is created. Then, the hard clauses
        are formatted to length 3 in another formula
        """
        # Formula with soft clauses of length 1
        formula1 = WCNFFormula()
        formula1.extend_vars(self.num_vars)

        # Soft clauses to length 1
        for clause in self.soft:
            if len(clause[1]) == 1:  # Add those already with length 1
                formula1.add_clause(clause[1], clause[0])
                continue

            # Format those with length > 1: create reification variable
            reif_var = formula1.new_var()

            # Add soft clause with reification variable
            formula1.add_clause([-reif_var], clause[0])

            # Add hard clause
            formula1.add_clause(clause[1] + [reif_var], 0)

        # Bulk add hard clauses
        formula1.add_clauses(self.hard)

        # Formula with hard clauses of length 3
        formula13 = WCNFFormula()
        formula13.extend_vars(formula1.num_vars)

        # Bulk add soft clauses
        for clause in formula1.soft:
            formula13.add_clause(clause[1], clause[0])

        # Hard clauses to length 3
        for clause in formula1.hard:
            formula13._hard_to_len_3(clause)

        return formula13

    def sum_soft_weights(self):
        """Return the sum of soft weights in the formula."""
        return self._sum_soft_weights

    def write_dimacs(self, stream=sys.stdout):
        """Write the formula in DIMACS format into the specified stream.

        :param stream: A writable stream object.
        """
        for line in self.header:
            print("c", line, file=stream)

        top = self.top_weight
        print("p wcnf", self.num_vars, self.num_clauses, top, file=stream)

        print("c ===== Hard Clauses =====", file=stream)
        for clause in self.hard:
            print(top, " ".join(str(l) for l in clause), "0", file=stream)

        print("c ===== Soft Clauses (Sum weights: {0}) ====="
              .format(self._sum_soft_weights), file=stream)
        for weight, clause in self.soft:
            print(weight, " ".join(str(l) for l in clause), "0", file=stream)

    def write_dimacs_file(self, file_path):
        """Write the formula in DIMACS format into the specified file.

        :param file_path: Path to a writable file.
        """
        with open(file_path, 'w') as stream:
            self.write_dimacs(stream)

    def _add_clause(self, literals, weight):
        if weight < 1:
            self.hard.append(literals)
        else:
            self.soft.append((weight, literals))
            self._sum_soft_weights += weight

    def _check_literals(self, literals):
        for var in map(abs, literals):
            if var == 0:
                raise WCNFException("Clause cannot contain variable 0")
            elif self.num_vars < var:
                raise WCNFException("Clause contains variable {0}, not defined"
                                    " by new_var()".format(var))

    def _hard_to_len_3(self, clause):
        """Split a clause into length 3 clauses."""
        # Extend clause if length is <= 3
        if len(clause) <= 3:
            additionals = [clause[0]] * (3 - len(clause))
            self.add_clause(clause + additionals, 0)
        else:
            new_var = self.new_var()
            self.add_clause(clause[:2] + [new_var], 0)
            self._hard_to_len_3([-new_var] + clause[2:])

    def __str__(self):
        """Convert formula to string."""
        stream = io.StringIO()
        self.write_dimacs(stream=stream)
        output = stream.getvalue()
        stream.close()
        return output


# Module functions
###############################################################################

def load_from_file(path, strict=False):
    """Load a WCNF from a file."""
    with open(path, 'r') as stream:
        return load_from_stream(stream, strict)


def load_from_stream(stream, strict=False):
    """Load a WCNF from a stream."""
    reader = ((l.strip(), l_no) for l_no, l in enumerate(stream, start=1))
    reader = ((l, l_no) for l, l_no in reader if l and not l.startswith("c"))
    f_type, n_clauses, n_vars, top = None, -1, -1, -1

    formula = WCNFFormula()

    def get_clause(values):
        return (values[0], values[1:]) if top > 0 else (1, values)

    for l, l_no in reader:
        v = l.split()
        if v[0] == 'p' and f_type is None:
            if 4 <= len(v) <= 5:
                f_type = v[1]
                if v[1] == 'cnf':
                    n_vars, n_clauses = int(v[2]), int(v[3])
                elif v[1] == 'wcnf':
                    n_vars, n_clauses, top = int(v[2]), int(v[3]), int(v[4])
                else:
                    raise WCNFException("Invalid formula type: " + v[1])
            else:
                raise WCNFException("Invalid number of elements at line {0}"
                                    .format(l_no))
        elif f_type is not None:
            values = [int(e) for e in v]
            raw_clauses = [list(g) for k, g in
                           itertools.groupby(values, lambda x: x == 0)
                           if not k]

            for r_clause in raw_clauses:
                w, c = get_clause(r_clause)
                if not c:
                    raise WCNFException("Clause without literals at line {0}"
                                        .format(l_no))

                highest_var = max(abs(l) for l in c)
                while formula.num_vars < highest_var:
                    formula.new_var()
                formula.add_clause(c, TOP_WEIGHT if w == top else w)
        else:
            raise WCNFException("Clause found before preamble")

    if strict and formula.num_vars != n_vars:
        raise ValueError("incorrect number of variables (preamble: {},"
                         " found: {})".format(n_vars, formula.num_vars))
    if strict and formula.num_clauses != n_clauses:
        raise ValueError("incorrect number of clauses (preamble: {},"
                         " found: {})".format(n_clauses, formula.num_clauses))

    return formula


if __name__ == "__main__":
    if len(sys.argv) == 3:
        # Read formula
        formula = load_from_file(sys.argv[1], strict=True)
        # Convert to 1-3 WPMS
        formula_1_3 = formula.to_13wpm()
        # Check formula
        print("Is formula in 1-3 WPMS:", formula_1_3.is_13wpm(strict=True))
        # Store new formula
        formula_1_3.write_dimacs_file(sys.argv[2])
        print("- New 1-3 WPMS formula written to", sys.argv[2])
    else:
        # Wrong number of arguments
        print("Usage: {} <in DIMACS> <out 1-3 wpms DIMACS>"
              .format(sys.argv[0])
              )
