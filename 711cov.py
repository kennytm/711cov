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
from os import walk
from os.path import splitext, join


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
                        help='the root directory to search for *.gcno files.')
    return parser


def find_all_gcno(root_dir: str) -> iter([str]):
    """
    Find all *.gcno files inside the root directory. Return an iterator of the
    full paths to those *.gcno files.
    """
    for dirpath, dirnames, filenames in walk(root_dir):
        for fn in filenames:
            if splitext(fn)[1] == '.gcno':
                yield join(dirpath, fn)


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    for fn in find_all_gcno(args.root):
        print(fn)

if __name__ == '__main__':
    main()

