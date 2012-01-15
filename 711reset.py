#!/usr/bin/env python3
#
#{{{ GPLv3 #####################################################################
#
# 711reset.py --- Delete all *.gcda files
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
from os import remove
from lib711cov import find_with_ext
from os.path import curdir

def build_arg_parser() -> ArgumentParser:
    """
    Construct an parser to parse the command line arguments.
    """
    parser = ArgumentParser(description='Remove all *.gcda files inside a root directory')
    parser.add_argument('gcda_root', metavar='GCDA_ROOT',
                        help='the root directory to search for *.gcda files. ')
    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    for gcda_file in find_with_ext(args.gcda_root, curdir, '.gcda'):
        remove(gcda_file)


if __name__ == '__main__':
    main()

