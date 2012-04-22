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
from subprocess import check_call, Popen, PIPE
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
        dirnames[:] = [x for x in dirnames if x not in {'.git'}]
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
    options = [gcov_bin, '--branch-probabilities',
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


class SourceBranch(object):
    """
    Represents a branch in a source line.
    """
    regex = re.compile(r'''
        (?P<type> branch|call)\s+
        (?P<id> \d+)\s
        (?:
            never\sexecuted
        |
            (?:taken|returned)\s
            (?P<count> \d+)
            (?:
                \s+\( (?P<info> [^)]*) \)
            )?
        )''', re.X)

    def __init__(self, count: int, id_: int, type_: str, info: str or None):
        self.count = count
        self.id_ = id_
        self.type_ = type_
        self.info = info

    @classmethod
    def from_gcov_match(cls, match: re.match):
        count = int(match.group('count') or '0')
        id_ = int(match.group('id'))
        type_ = match.group('type')
        info = match.group('info')
        return cls(count, id_, type_, info)

    def to_html(self) -> str:
        """
        Convert the source line to HTML representation.
        """
        if self.count:
            class_name = 'branch-taken'
            symbol = '▷' if self.type_ == 'branch' else '○'
        else:
            class_name = 'branch-not-taken'
            symbol = '▶' if self.type_ == 'branch' else '●'

        info_text = ' (' + self.info + ')' if self.info else ''
        return '<span class="branch {}" title="{} {}{} × {}">{}</span>'.format(
            class_name, self.type_, self.id_, info_text, self.count, symbol
        )

    def combine(self, other) -> None:
        """
        Combine this with another SourceBranch object representing the same branch.
        """
        assert self.id_ == other.id_
        assert self.type_ == other.type_
        self.count += other.count


class SourceLine(object):
    """
    Represents a line of source code.
    """
    regex = re.compile(r'\s*(-|#{5}|={5}|\d+):\s*([1-9]\d*):(.*)')

    def __init__(self, linenum: int, source: str, coverage: int):
        self.linenum = linenum
        self.source = source
        self.coverage = coverage
        self.branches = {}

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

        sorted_branches = sorted(self.branches.values(), key=lambda s: s.id_)
        branches_html = ''.join(b.to_html() for b in sorted_branches)

        return '<tr id="line-{2}" class="cov-health-{0}"><td>{4}</td><td>{1}</td><td>{2}</td><td>{3}</td></tr>\n'.format(
            coverage_class, coverage_str, self.linenum, escape(self.source),
            branches_html
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
        for branch in other.values():
            self.add_branch(branch)

    def add_branch(self, branch: SourceBranch) -> None:
        """
        Insert a branch information to this line.
        """
        branch_id = branch.id_
        if branch_id in self.branches:
            self.branches[branch_id].combine(branch)
        else:
            self.branches[branch_id] = branch


class SourceFunction(object):
    """
    Represents a function.
    """
    regex = re.compile(r'function (\S+) called (\d+) returned (\d+)% blocks executed (\d+)%')

    def __init__(self, name: str, linenum: int, called: int, returned: int, blocks: int):
        self.name = name
        self.linenum = linenum
        self.pretty_name = name
        self.called = called
        self.returned = returned
        self.blocks = blocks

    @classmethod
    def from_gcov_match(cls, linenum: int, match: re.match):
        (name, called_str, returned_str, blocks_str) = match.groups()
        return cls(name, linenum, int(called_str), int(returned_str), int(blocks_str))

    def to_html(self) -> str:
        """
        Convert the function to HTML representation.
        """
        coverage_class = 'zero' if self.called == 0 else 'all'
        return '''<tr id="func-{}" class="cov-health-{}">
                    <td><a href="#line-{}">{}</a></td>
                    <td>{}</td><td>{}%</td><td>{}%</td>
                </tr>\n'''.format(
            self.name, coverage_class, self.linenum, self.pretty_name, self.called,
            self.returned, self.blocks
        )

    def combine(self, other) -> None:
        assert self.name == other.name
        self.called += other.called
        self.returned = max(self.returned, other.returned)
        self.blocks = max(self.blocks, other.blocks)


class SourceFile(object):
    """
    Represents a source file.
    """
    def __init__(self):
        self.source_code = []
        self.source_functions = []
        self.source_name = ''

    def add(self, gcov_filename: str):
        """
        Add the analysis of a *.gcov file into this source file.
        """

        # Step 1: Read the file.
        source_lines = []
        source_functions = []
        with open(gcov_filename, 'r', errors='replace') as f:
            for line in f:
                source_match = SourceLine.regex.match(line)
                if source_match:
                    source_lines.append(SourceLine.from_gcov_match(source_match))
                    continue
                branch_match = SourceBranch.regex.match(line)
                if branch_match:
                    source_lines[-1].add_branch(SourceBranch.from_gcov_match(branch_match))
                    continue
                function_match = SourceFunction.regex.match(line)
                if function_match:
                    if source_lines:
                        linenum = source_lines[-1].linenum + 1
                    else:
                        linenum = 1
                    source_functions.append(SourceFunction.from_gcov_match(linenum, function_match))
                    continue

        # Step 2: Combine.
        if self.source_code:
            for orig, new in zip(self.source_code, source_lines):
                orig.combine(new)
        else:
            self.source_code = source_lines
        if self.source_functions:
            for orig, new in zip(self.source_functions, source_functions):
                orig.combine(new)
        else:
            self.source_functions = source_functions

    def coverage_stats(self) -> (int, int):
        """
        Return the coverage statistics. The first element is the number of lines
        covered, and the second element is the total number of source lines.
        """
        covered = sum(1 for line in self.source_code if line.coverage > 0)
        lines = sum(1 for line in self.source_code if line.coverage >= 0)
        return (covered, lines)

    def branch_stats(self) -> (int, int, int, int):
        br_covered = 0
        br_count = 0
        calls_covered = 0
        calls_count = 0
        for line in self.source_code:
            branches = [b for b in line.branches.values() if b.type_ == 'branch']
            calls = [b for b in line.branches.values() if b.type_ == 'call']
            br_covered += sum(1 for b in branches if b.count > 0)
            br_count += len(branches)
            calls_covered += sum(1 for b in calls if b.count > 0)
            calls_count += len(calls)
        return (br_covered, br_count, calls_covered, calls_count)

    def function_stats(self) -> (int, int):
        covered = sum(1 for func in self.source_functions if func.called > 0)
        funcs = len(self.source_functions)
        return (covered, funcs)

    def decode_cpp_function_names(self) -> None:
        """
        Decode the C++ function names.
        """
        with Popen(['c++filt'], stdin=PIPE, stdout=PIPE, universal_newlines=True) as proc:
            for func in self.source_functions:
                proc.stdin.write(func.name + '\n')
                func.pretty_name = proc.stdout.readline().rstrip('\n\r')

    def to_html(self) -> str:
        """
        Convert the source code to HTML representation.
        """
        source_name = escape(self.source_name)
        (covered, lines) = self.coverage_stats()
        lines_stats = "{} / {} ({} lines of code)".format(covered, lines, len(self.source_code))
        (br_covered, br_count, calls_covered, calls_count) = self.branch_stats()
        branch_stats = "{} / {}".format(br_covered, br_count)
        call_stats = "{} / {}".format(calls_covered, calls_count)
        (fn_covered, fn_count) = self.function_stats()
        fn_stats = "{} / {}".format(fn_covered, fn_count)

        self.decode_cpp_function_names()

        result = ["""
        <!DOCTYPE html>
        <html>
        <head>
        <title>Coverage report of file """ + source_name + """</title>
        <style type="text/css">
        /*<![CDATA[*/
        .cov-health-zero td { color: white; }
        .cov-health-zero a { color: #CCCCFF; }
        .cov-health-zero a:visited { color: #FFCCFF; }
        .cov-health-zero:nth-child(odd) td { background-color: #CC0000; }
        .cov-health-zero:nth-child(even) td { background-color: #DD0000; }
        .cov-health-na td { color: silver; }
        .cov-health-na td:nth-child(2) { visibility: hidden; }
        .branch { cursor: help; }
        .branch-taken { color: silver; }
        .branch-taken:hover { color: black; }
        .branch-not-taken { color: red; }
        .branch-not-taken:hover { color: maroon; }
        #source tbody td:last-child, #funcs tbody td:first-child
            { text-align: left; font-family: monospace; white-space: pre; }
        .sortable { border-collapse: collapse; }
        div {  width: 100%; overflow: hidden; }
        .sortable td { text-align: right; padding-left: 2em; }
        .sortable tbody tr:nth-child(odd) { background-color: #FFFFCC; }
        .sortable tbody tr:nth-child(even) { background-color: #FFFFDD; }
        #source tbody tr:hover td:last-child { font-weight: bold; }
        #source tbody td:first-child { max-width: 7em; font-size: smaller; word-wrap: break-word; }
        #source tbody td:nth-child(2) { font-size: smaller; color: silver; }
        #summary { float: right; border-collapse: collapse;  }
        #summary td { border: 1px solid black; }
        caption { font-weight: bold; }
        /*]]>*/
        </style>
        <script src="sorttable.js"></script>
        </head>
        <body>
        <p><a href="index.html">&lArr; Back</a> | Go to line #<input type="number" id="goto" /></p>
        <h1>""" + source_name + """</h1>
        <div>
        <table id="summary">
        <caption>Summary</caption>
        <tr><td>Lines</td><td>""" + lines_stats + """</td></tr>
        <tr><td>Branches</td><td>""" + branch_stats + """</td></tr>
        <tr><td>Calls</td><td>""" + call_stats + """</td></tr>
        <tr><td><a href="#functions">Functions</a></td><td>""" + fn_stats + """</td></tr>
        </ul>
        </table>
        <table class="sortable" id="source">
        <thead><tr><th>Branches</th><th>Cov</th><th>Line</th><th class="sorttable_nosort">Source</th></tr></thead>
        <tbody>
        """]
        result.extend(line.to_html() for line in self.source_code)
        result.append("""
        </tbody>
        </table>
        </div>
        <h2 id="functions">Functions</h2>
        <div>
        <table class="sortable" id="funcs">
        <thead><tr><th>Function</th><th>Calls</th><th>Ret.</th><th>Blk. Exec.</th></tr></thead>
        <tbody>""")
        result.extend(func.to_html() for func in self.source_functions)
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


def to_percentage(covered: int, total: int, good_percent: float, normal_percent: float) -> (str, str):
    if total == 0:
        return ('---', 'na')
    elif covered == total:
        return ('100.00', 'all')
    elif covered == 0:
        return ('0.00', 'zero')

    percent = (100 * covered) / total
    coverage_percent = '{:.2f}'.format(percent)
    if coverage_percent == '100.00':
        coverage_percent = '99.99'
    elif coverage_percent == '0.00':
        coverage_percent = '0.01'
    if percent >= good_percent:
        coverage_health = 'good'
    elif percent >= normal_percent:
        coverage_health = 'normal'
    else:
        coverage_health = 'bad'
    return (coverage_percent, coverage_health)


def html_index(source_files: iter([SourceFile]), compile_root: str) -> str:
    """
    Generate the index page to the coverage reports.
    """
    def single_summary(source_file: SourceFile) -> str:
        (covered, lines) = source_file.coverage_stats()
        (br_covered, br_count, _, _) = source_file.branch_stats()
        (fn_covered, fn_count) = source_file.function_stats()
        (coverage_percent, coverage_health) = to_percentage(covered, lines, 90, 75)
        (branch_percent, branch_health) = to_percentage(br_covered, br_count, 75, 50)
        (fn_percent, fn_health) = to_percentage(fn_covered, fn_count, 90, 75)


        return '''<tr>
                    <td><a href="{}">{}</a></td>
                    <td class="cov-health-{}" title="{}/{}">{}%</td>
                    <td class="cov-health-{}" title="{}/{}">{}%</td>
                    <td class="cov-health-{}" title="{}/{}">{}%</td>
                  </tr>'''.format(
            to_html_filename(source_file.source_name),
            escape(source_file.source_name),
            coverage_health, covered, lines, coverage_percent,
            branch_health, br_covered, br_count, branch_percent,
            fn_health, fn_covered, fn_count, fn_percent
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
    td { text-align: right; padding: 0.1em 0.5em; }
    td:first-child { text-align: left; }
    table { border-collapse: collapse; }
    tr { border: 1px solid black; }
    /*]]>*/
    </style>
    <script src="sorttable.js"></script>
    </head>
    <body>
    <h1>Coverage report for """ + title + """</h1>
    <div><table class="sortable">
    <thead><tr><th>File</th><th>Lines</th><th>Branch</th><th>Functions</th></tr></thead>
    <tbody>
    """]

    html_res.extend(single_summary(s) for s in source_files)
    html_res.append('</tbody></table></div></body></html>')

    return '\n'.join(html_res)




