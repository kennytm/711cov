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
from os import walk, chdir, listdir, getcwd
from os.path import splitext, join, abspath, relpath
from tempfile import mkdtemp
from subprocess import check_call
from shutil import move


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
                        help='the root directory to search for *.gcno files. '
                             'It must be writable, and does not contain any '
                             '*.gcov files.')
    parser.add_argument('compile_root', metavar='COMPILE_ROOT',
                        help='from where the source files are compiled.')
    return parser


def find_all_gcno(abs_root: str, compile_root: str) -> iter([str]):
    """
    Find all *.gcno files inside the root directory. Return an iterator of the
    relative paths to those *.gcno files from 'compile_root'.
    """
    for dirpath, dirnames, filenames in walk(abs_root):
        rpath = relpath(dirpath, start=compile_root)
        for fn in filenames:
            if splitext(fn)[1] == '.gcno':
                yield join(rpath, fn)


def gcov(gcov_bin: str, compile_root: str, gcno_files: iter([str])) -> str or None:
    """
    Perform 'gcov' on all *.gcno files from the iterator, putting the result
    *.gcov files to 'compile_root'. Returns whether 'gcov' finished
    successfully.
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
        return None

    print('\033[1;34m==> 711cov:\033[0m Found', gcno_count, '*.gcno files')

    # Invoke gcov
    tmpdir = mkdtemp(prefix='711cov_')
    chdir(compile_root)
    with open('/dev/null', 'w') as null_file:
        check_call(options, stdout=null_file)
    move_gcov('.', tmpdir)
    return tmpdir


def move_gcov(source_dir: str, target_dir: str) -> None:
    """
    Move all *.gcov files from 'source_dir' to 'target_dir'.
    """
    for fn in listdir(source_dir):
        if splitext(fn)[1] == '.gcov':
            move(join(source_dir, fn), target_dir)


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    gcno_files = find_all_gcno(args.gcno_root, args.compile_root)
    res_dir = gcov(args.gcov, args.compile_root, gcno_files)
    if not res_dir:
        print('\033[1;31m==> 711cov:\033[0m No *.gcno files found in', args.gcno_root)
        return 1

    print(res_dir)
    return 0


if __name__ == '__main__':
    err_code = main()
    exit(err_code)

