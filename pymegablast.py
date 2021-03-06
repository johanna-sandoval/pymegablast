#!/usr/bin/env python

# pymegablast is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.

# pymegablast is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.

# You should have received a copy of the GNU General Public License along with
# pymegablast.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Louis-Philippe Lemieux Perreault"
__copyright__ = ("Copyright 2014 Louis-Philippe Lemieux Perreault. "
                 "All rights reserved.")
__license__ = "GNU General Public"
__credits__ = ["Louis-Philippe Lemieux Perreault", ]
__version__ = "0.3"
__maintainer__ = "Louis-Philippe Lemieux Perreault"
__email__ = "louis-philippe.lemieux.perreault@statgen.org"
__status__ = "Development"


import os
import sys
import shutil
import argparse
from datetime import datetime
from collections import Counter
from subprocess import check_output, CalledProcessError

from Bio import SeqIO


def main():
    """The main function."""
    # Creating the argument parser
    desc = """Runs pymegablast (version {}).""".format(__version__)
    parser = argparse.ArgumentParser(description=desc)

    # Executing
    try:
        # Getting and checking the options
        args = parse_args(parser)
        check_args(args)

        # Printing the version of the script
        print "pymegablast version {}".format(__version__)

        # Creating the output directory
        if not os.path.isdir(args.output_dir):
            os.mkdir(args.output_dir)

        # Do we need to split the input sequence?
        sequence_file = os.path.join(args.output_dir, "megablast_input.fasta")
        if args.window:
            # We split
            split_fasta_sequences(args.input, args.window_length,
                                  sequence_file)

        else:
            # We don't split, so just copy the file
            shutil.copyfile(args.input, sequence_file)

        # Running megablast
        results = run_megablast(sequence_file, args.output_dir, args)

        # Parsing the results
        results = parse_results(results)

        # Now generate the final output
        generate_final_output(results, sequence_file, args.output_dir)

    except KeyboardInterrupt:
        print >>sys.stderr, "Cancelled by user"
        sys.exit(0)

    except ProgramError as e:
        parser.error(e.message)


def generate_final_output(results, sequence_file, output_dir):
    """Generate the final report.

    :param results: a counter of sequence
    :param sequence_file: the fasta file containing the sequences
    :output_dir: the output directory

    :type results: collections.Counter

    """
    # The output file
    o_file = None
    try:
        o_file = open(os.path.join(output_dir, "final_report.txt"), 'w')
    except IOError:
        msg = "can't write to {}".format(output_dir)
        raise ProgramError(msg)

    for seq in SeqIO.parse(sequence_file, "fasta"):
        print >>o_file, "\t".join([seq.id, str(seq.seq), str(results[seq.id])])

    # Closing the file
    o_file.close()


def parse_results(results):
    """Parse the megablast results.

    :param results: the megablast results

    :type results: list of strings

    :returns: a counter of sequences.

    """
    # Removes the comment lines at the beginning of the output
    while results[0].startswith("#"):
        del results[0]

    # Count the number of appearance of each sequence
    counter = Counter([i.split("\t")[0] for i in results])

    return counter


def run_megablast(sequence_file, output_dir, options):
    """Runs megablast with options.

    :param sequence_file: the name of the sequence file
    :param output_dir: the output directory
    :param options: the options

    :type sequence_file: string
    :type output_dir: string
    :type options: Namespace

    :returns: a list of the output.

    """
    output = None
    try:
        print
        output = check_output(["megablast",
                               "-d", options.database,
                               "-i", sequence_file,
                               "-D 3",
                               "-W", str(options.word_size),
                               "-s", str(options.minimal_hit_score)])
        print

    except OSError:
        msg = "megablast: command not found"
        raise ProgramError(msg)

    except CalledProcessError:
        msg = "megablast: problem with megablast"
        raise ProgramError(msg)

    # Splitting the output
    output = output.split("\n")

    # Opening the output file
    o_file = None
    try:
        o_file = open(os.path.join(output_dir, "megablast_results.txt"), "w")

    except IOError:
        msg = "can't write file to {}".format(output_dir)
        raise ProgramError(msg)

    # Writing the results
    for line in output:
        print >>o_file, line

    # Closing the file
    o_file.close()

    return output


def split_fasta_sequences(input_file, window_length, output_file):
    """Split sequences (fasta format) with window.

    :param input_file: the input file (sequence(s) in fasta format).
    :param window_length: the length of the window.
    :param output_file: the name of the output file.

    :type input_file: string
    :type window_length: int
    :type output_directory: string

    Split sequence(s) from a fasta file using a window length (w). The first
    sub-sequence will be from 1:1+w, then from 2:2+w, etc. For example, if the
    sequence is ``ACTG`` and w=2, the output is ``AC``, ``CT`` and ``TG``. If
    w=3, then the output is ``ACT`` and ``CTG``.

    """
    sequences = []
    for seq in SeqIO.parse(input_file, "fasta"):
        if len(seq) <= window_length:
            # The sequence length is too small, so no splitting
            sequences.append(seq)
        else:
            nb = 0
            for i in xrange(0, len(seq) - window_length + 1):
                # We split at each window_length, then increase by 1
                nb += 1
                sequences.append(seq[i:i+window_length])
                sequences[-1].id = sequences[-1].id + "_{}".format(nb)
                sequences[-1].description = (
                    "{}, window {}".format(sequences[-1].description, nb))

    # Writing the sequences to file
    SeqIO.write(sequences, output_file, "fasta")


def check_args(args):
    """Checks the arguments and options.

    :param args: an object containing the options and arguments of the program.

    :type args: :py:class:`argparse.Namespace`

    :returns: ``True`` if everything was OK.

    If there is a problem with an option, an exception is raised using the
    :py:class:`ProgramError` class, a message is printed to the
    :class:`sys.stderr` and the program exits with error code 1.

    """
    # Check the input file
    if not os.path.isfile(args.input):
        msg = "{}: no such file".format(args.input)
        raise ProgramError(msg)

    # Check the window size
    if args.window:
        if args.window_length < 0:
            msg = "window size: invalid value {}".format(args.window_length)
            raise ProgramError(msg)
    return True


def parse_args(parser):
    """Parses the command line options and arguments.

    :returns: A :py:class:`argparse.Namespace` object created by the
              :py:mod:`argparse` module. It contains the values of the
              different options.

    .. note::
        No option check is done here (except for the one automatically done by
        :py:mod:`argparse`). Those need to be done elsewhere (see
        :py:func:`checkArgs`).

    """
    # General options
    parser.add_argument("-v", "--version", action="version",
                        version="%(prog)s {}".format(__version__))

    # Input file options
    group = parser.add_argument_group("Input Files")
    group.add_argument("-i", "--input", type=str, metavar="FILE",
                       required=True, help=("The file containing the "
                                            "sequence(s)."))

    # The sequence pre-processing options
    group = parser.add_argument_group("Sequence(s) Pre-Processing")
    group.add_argument("-w", "--window", action="store_true",
                       help=("If set to True, the sequence(s) will be split "
                             "by a window of X characters (see "
                             "-wl/--window-length option). "
                             "[Default: False]"))
    group.add_argument("-wl", "--window-length", type=int, metavar="INT",
                       default=20, help=("The window size (if -w/--window "
                                         "option is used). "
                                         "[Default: %(default)d]"))

    # The megablast options
    group = parser.add_argument_group("MegaBlast Options")
    group.add_argument("-d", "--database", type=str, metavar="PATH",
                       default=os.path.join(os.sep, "mnt", "isi",
                                            "reference", "Genome_Build_37",
                                            "chromosomes"),
                       help=("The database to use for the search. "
                             "[Default: %(default)s]"))
    group.add_argument("-W", "--word-size", type=int, metavar="INT",
                       default=10, help=("The word size for MegaBlast. "
                                         "[Default: %(default)d]"))
    group.add_argument("-s", "--minimal-hit-score", type=int, metavar="INT",
                       default=17, help=("The minimal hit score for "
                                         "MegaBlast. [Default: "
                                         "%(default)d]"))

    # Were to save the output files
    group = parser.add_argument_group("Output Files")
    group.add_argument("-o", "--output-dir", type=str, metavar="DIR",
                       default="megablast.{}".format(
                               datetime.today().strftime("%Y-%m-%d_%H.%M.%S")),
                       help=("The name of the output directory. "
                             "[Default: %(default)s]"))

    return parser.parse_args()


class ProgramError(Exception):
    """An :py:class:`Exception` raised in case of a problem.

    :param msg: the message to print to the user before exiting.
    :type msg: string

    """
    def __init__(self, msg):
        """Construction of the :py:class:`ProgramError` class.

        :param msg: the message to print to the user
        :type msg: string

        """
        self.message = str(msg)

    def __str__(self):
        return self.message


# Calling the main, if necessary
if __name__ == "__main__":
    main()
