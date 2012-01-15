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
from os.path import splitext, join, abspath, relpath, dirname
from tempfile import mkdtemp
from subprocess import check_call
from shutil import move, copy
from collections import defaultdict
from html import escape
from urllib.parse import quote
import re


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

def unmangle_gcov_filename(gcov_filename: str):
    """
    Convert the *.gcov filenames (e.g. "#usr#include#stdio.h") back to a path.
    """
    return gcov_filename.replace('^', '..').replace('#', '/').replace('~', ':')


class SourceLine(object):
    """
    Represents a line of source code.
    """
    normal_source_re = re.compile(r'\s*(-|#{5}|={5}|\d+):\s*([1-9]\d*):(.*)')

    def __init__(self, linenum: int, source: str, coverage: int):
        self.linenum = linenum
        self.source = source
        self.coverage = coverage

    @classmethod
    def from_gcov_match(cls, match: re.match):
        (coverage_str, linenum_str, source) = match.groups()
        if coverage_str == '-':
            coverage = -1
        elif coverage_str in ('#####', '====='):
            coverage = 0
        else:
            coverage = int(coverage_str)
        return cls(int(linenum_str), source, coverage)


    def to_html(self) -> str:
        """
        Convert the source line to HTML representation.
        """
        if self.coverage < 0:
            coverage_str = '1e308'
            coverage_class = 'na'
        elif self.coverage == 0:
            coverage_str = '0'
            coverage_class = 'zero'
        else:
            coverage_str = str(self.coverage)
            coverage_class = 'all'

        return '<tr id="line-{2}" class="cov-health-{0}"><td>{1}</td><td>{2}</td><td>{3}</td></tr>\n'.format(
            coverage_class, coverage_str, self.linenum, escape(self.source),
        )

    def combine(self, other) -> None:
        """
        Combine this with another SourceLine object representing the same line.
        """
        assert self.linenum == other.linenum
        assert self.source == other.source
        if other.coverage >= 0:
            if self.coverage < 0:
                self.coverage = other.coverage
            else:
                self.coverage += other.coverage


class SourceFile(object):
    """
    Represents a source file.
    """
    def __init__(self):
        self.source_code = []
        self.source_name = ''

    def add(self, gcov_filename: str):
        """
        Add the analysis of a *.gcov file into this source file.
        """

        # Step 1: Read the file.
        source_lines = []
        with open(gcov_filename, 'r') as f:
            for line in f:
                source_match = SourceLine.normal_source_re.match(line)
                if source_match:
                    source_lines.append(SourceLine.from_gcov_match(source_match))
                    continue

        # Step 2: Combine.
        if self.source_code:
            for orig, new in zip(self.source_code, source_lines):
                orig.combine(new)
        else:
            self.source_code = source_lines

    def coverage_stats(self) -> (int, int):
        """
        Return the coverage statistics. The first element is the number of lines
        covered, and the second element is the total number of source lines.
        """
        covered = sum(1 for line in self.source_code if line.coverage > 0)
        lines = sum(1 for line in self.source_code if line.coverage >= 0)
        return (covered, lines)

    def to_html(self) -> str:
        """
        Convert the source code to HTML representation.
        """
        source_name = escape(self.source_name)

        result = ["""
        <!DOCTYPE html>
        <html>
        <head>
        <title>Coverage report of file """ + source_name + """</title>
        <style type="text/css">
        /*<![CDATA[*/
        .cov-health-zero td { color: white; }
        .cov-health-zero:nth-child(odd) td { background-color: #CC0000; }
        .cov-health-zero:nth-child(even) td { background-color: #DD0000; }
        .cov-health-na td { color: silver; }
        .cov-health-na td:first-child { visibility: hidden; }
        tbody td:last-child { text-align: left; font-family: monospace;
                              white-space: pre; }
        table { border-collapse: collapse; }
        div {  width: 100%; overflow: hidden; }
        td { text-align: right; padding-left: 2em; }
        tbody tr:nth-child(odd) { background-color: #FFFFCC; }
        tbody tr:nth-child(even) { background-color: #FFFFDD; }
        tbody tr:hover td:last-child { font-weight: bold; }
        tbody td:nth-child(2) { font-size: smaller; color: silver; }
        /*]]>*/
        </style>
        <script src="sorttable.js"></script>
        </head>
        <body>
        <p><a href="index.html">&lArr; Back</a> | Go to line #<input type="number" id="goto" /></p>
        <h1>""" + source_name + """</h1>
        <div><table class="sortable">
        <thead><tr><th>Cov</th><th>Line</th><th class="sorttable_nosort">Source</th></tr></thead>
        <tbody>
        """]
        result.extend(line.to_html() for line in self.source_code)
        result.append("""
        </tbody>
        </table>
        </div>
        <script>
        //<![CDATA[
        document.getElementById('goto').onchange = function()
        {
            location = "#line-" + this.value;
        }
        //]]>
        </script>
        </body>
        </html>
        """)
        return '\n'.join(result)


def collect_gcov(gcov_dir: str, abs_compile_root: str, ignored_prefixes = ('/usr',)) -> iter([SourceFile]):
    """
    Collect all *.gcov files inside 'gcov_dir', but ignore those with a path
    starting with 'ignored_prefixes'.
    """
    res_dict = defaultdict(SourceFile)
    for filename in listdir(gcov_dir):
        (fn, ext) = splitext(filename)
        if ext != '.gcov':
            continue

        source_fn = unmangle_gcov_filename(fn)
        if source_fn.startswith(ignored_prefixes):
            continue

        rel_source_fn = relpath(source_fn, start=abs_compile_root)
        res_dict[rel_source_fn].add(join(gcov_dir, filename))

    for source_name, source_file in sorted(res_dict.items()):
        source_file.source_name = source_name
        yield source_file


def to_html_filename(source_file_name: str) -> str:
    """
    Get the file name corresponding to the source file.
    """
    def escape_char(m: re.match) -> str:
        c = m.group()
        if c == '/':
            return '--'
        elif c == '-':
            return '-m'
        else:
            return '-' + hex(ord(c))[2:]

    return 'source-' + re.sub(r'[^.\w]', escape_char, source_file_name) + '.html'


def copy_sorttable_js(directory: str) -> None:
    """
    Copy 'sorttable.js' into the 'directory'.
    """
    copy(join(dirname(__file__), 'sorttable.js'), directory)



def html_index(source_files: iter([SourceFile]), compile_root: str) -> str:
    """
    Generate the index page to the coverage reports.
    """
    def single_summary(source_file: SourceFile) -> str:
        (covered, lines) = source_file.coverage_stats()
        if lines == 0:
            coverage_percent = '---'
            coverage_health = 'na'
        elif covered == lines:
            coverage_percent = '100.00'
            coverage_health = 'all'
        elif covered == 0:
            coverage_percent = '0.00'
            coverage_health = 'zero'
        else:
            percent = (100 * covered) / lines
            coverage_percent = '{:.2f}'.format(percent)
            if coverage_percent == '100.00':
                coverage_percent = '99.99'
            elif coverage_percent == '0.00':
                coverage_percent = '0.01'
            if percent >= 90:
                coverage_health = 'good'
            elif percent >= 75:
                coverage_health = 'normal'
            else:
                coverage_health = 'bad'

        return '<tr><td><a href="{3}">{0}</a></td><td class="cov-health-{1}">{2}%</td>'.format(
            escape(source_file.source_name), coverage_health, coverage_percent,
            to_html_filename(source_file.source_name)
        )

    title = escape(compile_root)

    html_res = ["""
    <!DOCTYPE html>
    <html>
    <head>
    <title>Coverage report for """ + title + """</title>
    <style type="text/css">
    /*<![CDATA[*/
    .cov-health-all { background-color: #80FF80; }
    .cov-health-zero { background-color: black; color: white; }
    .cov-health-good { background-color: yellow; }
    .cov-health-normal { background-color: orange; }
    .cov-health-bad { background-color: red; }
    td:last-child { text-align: right; }
    table { border-collapse: collapse; }
    tr { border: 1px solid black; }
    td { padding: 2px; }
    /*]]>*/
    </style>
    <script src="sorttable.js"></script>
    </head>
    <body>
    <h1>Coverage report for """ + title + """</h1>
    <div><table class="sortable">
    <thead><tr><th>File</th><th>Line cov.</th></tr></thead>
    <tbody>
    """]

    html_res.extend(single_summary(s) for s in source_files)
    html_res.append('</tbody></table></div></body></html>')

    return '\n'.join(html_res)




