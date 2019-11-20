#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function

import argparse
import collections
import itertools
import os
import sys

import msat_runner
import wcnf


# Graph class
###############################################################################


class Graph(object):
    """
    This class represents an undirected graph.

    The graph nodes are labeled 1, ..., n, where n is the number of nodes,
    and the edges are stored as pairs of nodes.
    """

    def __init__(self, file_path=""):
        """Construct the Graph object."""
        self.edges = []
        self.n_nodes = 0

        if file_path:
            self.read_file(file_path)

    def read_file(self, file_path):
        """Load a graph from the given file.

        :param file_path: Path to the file that contains a graph definition.
        """
        with open(file_path, 'r') as stream:
            self.read_stream(stream)

    def read_stream(self, stream):
        """Load a graph from the given stream.

        :param stream: A data stream from which read the graph definition.
        """
        n_edges = -1
        edges = set()

        reader = (l for l in (ll.strip() for ll in stream) if l)
        for line in reader:
            line = line.split()
            if line[0] == 'p':
                self.n_nodes = int(line[2])
                n_edges = int(line[3])
            elif line[0] == 'c':
                pass  # Ignore comments
            else:
                edges.add(frozenset([int(line[1]), int(line[2])]))

        self.edges = tuple(tuple(x) for x in edges)
        if n_edges != len(edges):
            print("Warning incorrect number of edges")

    def visualize(self, name="graph"):
        """Visualize graph using 'graphviz' library.

        To install graphviz you can use 'pip install graphviz'.
        Notice that graphviz should also be installed in your system.
        For ubuntu, you can install it using 'sudo apt install graphviz'

        :param name: Name of the generated file, defaults to "graph"
        :type name: str, optional
        :raises ImportError: When unable to import graphviz.
        """
        try:
            from graphviz import Graph
        except ImportError:
            msg = (
                "Could not import 'graphviz' module. "
                "Make shure 'graphviz' is installed "
                "or install it typing 'pip install graphviz'"
            )
            raise ImportError(msg)

        # Create graph
        dot = Graph()
        # Create nodes
        for n in range(1, self.n_nodes + 1):
            dot.node(str(n))
        # Create edges
        for n1, n2 in self.edges:
            dot.edge(str(n1), str(n2))
        # Visualize
        dot.render(name, view=True, cleanup=True)

    def min_vertex_cover(self, solver):
        """Compute the minimum vertex cover of the graph.

        :param solver: An instance of MaxSATRunner.
        :return: A solution (list of nodes).
        """
        # Initialization
        formula = wcnf.WCNFFormula()
        nodes = [formula.new_var() for _ in range(self.n_nodes)]

        # Add nodes to formula as soft clauses
        formula.add_clauses([[-n] for n in nodes], 1)

        # Add edges as hard clauses
        # (works because edges have same domain as ctf vars)
        formula.add_clauses([[i, j] for i, j in self.edges])

        # Find solution
        solution = msat_runner.solve_formula(solver, formula)[1]

        # Translate back to problem domain
        return list(filter(lambda x: x > 0, solution))

    def max_clique(self, solver):
        """Compute the maximum clique of the graph.

        :param solver: An instance of MaxSATRunner.
        :return: A solution (list of nodes).
        """
        formula = wcnf.WCNFFormula()
        nodes = [formula.new_var() for _ in range(self.n_nodes)]

        # Soft clauses
        formula.add_clauses([[i] for i in nodes], 1)

        # Generate all edges in complete graph
        combinations = []
        for i in nodes:
            for j in nodes[i:]:
                combinations.append((i, j))

        # Hard clauses
        for i, j in combinations:
            if (i, j) not in self.edges:
                formula.add_clause([-i, -j], wcnf.TOP_WEIGHT)

        solution = msat_runner.solve_formula(solver, formula)[1]
        return list(filter(lambda x: x > 0, solution))

    def max_cut(self, solver):
        """Compute the maximum cut of the graph.

        :param solver: An instance of MaxSATRunner.
        :return: A solution (list of nodes).
        """
        formula = wcnf.WCNFFormula()
        [formula.new_var() for _ in range(self.n_nodes)]

        # Soft clauses
        formula.add_clauses(
            [[i, j] for i, j in self.edges] +
            [[-i, -j] for i, j in self.edges],
            1)

        solution = msat_runner.solve_formula(solver, formula)[1]
        return list(filter(lambda x: x > 0, solution))


# Program main
###############################################################################


def main(argv=None):
    """Run MVC, MCLIQUE and MCUT with the given graph and solver."""
    args = parse_command_line_arguments(argv)

    solver = msat_runner.MaxSATRunner(args.solver)
    graph = Graph(args.graph)
    if args.visualize:
        graph.visualize(os.path.basename(args.graph))

    min_vertex_cover = graph.min_vertex_cover(solver)
    print("MVC", " ".join(map(str, min_vertex_cover)))

    max_clique = graph.max_clique(solver)
    print("MCLIQUE", " ".join(map(str, max_clique)))

    max_cut = graph.max_cut(solver)
    print("MCUT", " ".join(map(str, max_cut)))


# Utilities
###############################################################################


def parse_command_line_arguments(argv=None):
    """Parse input arguments."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("solver", help="Path to the MaxSAT solver.")

    parser.add_argument("graph", help="Path to the file that describes the"
                                      " input graph.")

    parser.add_argument("--visualize", "-v", action="store_true",
                        help="Visualize graph (graphviz required)")

    return parser.parse_args(args=argv)


# Entry point
###############################################################################


if __name__ == "__main__":
    sys.exit(main())
