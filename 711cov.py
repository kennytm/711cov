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
from shutil import rmtree
from os import makedirs, getcwd, chdir
from lib711cov import *


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
    parser.add_argument('gcno_root', metavar='GCNO_ROOT',
                        help='the root directory to search for *.gcno files. ')
    parser.add_argument('compile_root', metavar='COMPILE_ROOT',
                        help='from where the source files are compiled.'
                             'It must be writable, and does not contain any '
                             '*.gcov files.')
    return parser


def main() -> int:
    cwd = getcwd()

    parser = build_arg_parser()
    args = parser.parse_args()
    abs_compile_root = abspath(args.compile_root)
    gcno_files = find_with_ext(args.gcno_root, args.compile_root, '.gcno')
    res_dir = gcov(args.gcov, args.compile_root, gcno_files)
    if not res_dir:
        return 1

    gcovs = list(collect_gcov(res_dir, abs_compile_root))

    chdir(cwd)
    try:
        makedirs(args.output)
    except OSError:
        pass
    copy_sorttable_js(args.output)
    chdir(args.output)
    with open('index.html', 'w') as f:
        f.write(html_index(gcovs, args.compile_root))

    rmtree(res_dir)
    return 0


if __name__ == '__main__':
    err_code = main()
    exit(err_code)


