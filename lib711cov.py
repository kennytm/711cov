#!/usr/bin/env python3
#
#{{{ GPLv3 #####################################################################
#
# lib711cov.py --- Code coverage reporting software for gcov-4.7 (library part).
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

from sys import exit
from os import walk, chdir, listdir, getcwd
from os.path import splitext, join, abspath, relpath
from tempfile import mkdtemp
from subprocess import check_call
from shutil import move


def find_with_ext(abs_root: str, compile_root: str, ext: str) -> iter([str]):
    """
    Find all files with a given extension inside the root directory. Return an
    iterator of the relative paths to those *.gcno files from 'compile_root'.
    """
    for dirpath, dirnames, filenames in walk(abs_root):
        rpath = relpath(dirpath, start=compile_root)
        for fn in filenames:
            if splitext(fn)[1] == ext:
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
        print('\033[1;31m==> 711cov:\033[0m No *.gcno files found')
        return None
    else:
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

