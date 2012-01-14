#!/usr/bin/env python3
#
#{{{ GPLv3 #####################################################################
#
# 711cov.py --- Code coverage reporting software for gcov-4.7.
# Copyright (C) 2012  kennytm (auraHT Ltd.)
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
#
#}}}############################################################################

from argparse import ArgumentParser
from sys import exit
from os import walk, chdir
from os.path import splitext, join, abspath
from tempfile import mkdtemp
from subprocess import check_call


def build_arg_parser() -> ArgumentParser:
    """
    Construct an parser to parse the command line arguments.
    """
    parser = ArgumentParser(description='Code coverage reporting software for gcov-4.7')
    parser.add_argument('--gcov',
                        default='/usr/bin/gcov-4.7',
                        help='path to the gcov executable.')
    parser.add_argument('-o', '--output', metavar='DIR',
                        default='./coverage-report/',
                        help='output directory to write the HTML report.')
    parser.add_argument('root', metavar='ROOT',
                        help='the root directory to search for *.gcno files. '
                             'It must be writable, and does not contain any '
                             '*.gcov files.')
    return parser


def find_all_gcno(abs_root: str) -> iter([str]):
    """
    Find all *.gcno files inside the root directory. Return an iterator of the
    full paths to those *.gcno files.
    """
    for dirpath, dirnames, filenames in walk(abs_root):
        for fn in filenames:
            if splitext(fn)[1] == '.gcno':
                yield join(dirpath, fn)


def gcov(gcov_bin: str, abs_root: str, gcno_files: iter([str])) -> bool:
    """
    Perform 'gcov' on all *.gcno files from the iterator, putting the result
    *.gcov files to 'abs_root'. Returns whether 'gcov' finished successfully.
    """

    # Construct the optinos. Make sure we have *.gcno files to parse.
    options = [gcov_bin, '--all-blocks',
                         '--branch-probabilities',
                         '--branch-counts',
                         '--preserve-paths']
    basic_options_length = len(options)
    options.extend(gcno_files)
    gcno_count = len(options) - basic_options_length
    if gcno_count == 0:
        return False

    print('\033[1;34m==> 711cov:\033[0m Found', gcno_count, '*.gcno files')

    # Invoke gcov
    chdir(abs_root)
    with open('/dev/null', 'w') as null_file:
        check_call(options, stdout=null_file)

    return True


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    abs_root = abspath(args.root)
    gcno_files = find_all_gcno(abs_root)
    if not gcov(args.gcov, abs_root, gcno_files):
        print('\033[1;31m==> 711cov:\033[0m No *.gcno files found in', abs_root)
        return 1

    return 0


if __name__ == '__main__':
    err_code = main()
    exit(err_code)

