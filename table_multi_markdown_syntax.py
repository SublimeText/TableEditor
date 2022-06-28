# table_multi_markdown_syntax.py - Support MultiMarkdown table syntax

# Copyright (C) 2012  Free Software Foundation, Inc.

# Author: Valery Kocubinsky
# Package: SublimeTableEditor
# Homepage: https://github.com/vkocubinsky/SublimeTableEditor

# This file is part of SublimeTableEditor.

# SublimeTableEditor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# SublimeTableEditor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with SublimeTableEditor.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import print_function
from __future__ import division

import math
import re


try:
    from . import table_base as tbase
    from . import table_line_parser as tparser
except ValueError:
    import table_base as tbase
    import table_line_parser as tparser


def create_syntax(table_configuration=None):
    return MultiMarkdownTableSyntax(table_configuration)


class MultiMarkdownTableSyntax(tbase.TableSyntax):

    def __init__(self, table_configuration):
        tbase.TableSyntax.__init__(self, "Multi Markdown", table_configuration)

        self.line_parser = tparser.LineParserPlus(r"(?:(?:\|\|+)|(?:\|))")
        self.table_parser = MultiMarkdownTableParser(self)
        self.table_driver = MultiMarkdownTableDriver(self)


class MultiMarkdownAlignColumn(tbase.Column):
    PATTERN = r"^\s*([:]?[-]+[:]?)\s*$"

    def __init__(self, row, data):
        tbase.Column.__init__(self, row)
        col = data.strip()
        if col.count(':') == 2:
            self._align_follow = tbase.Column.ALIGN_CENTER
        elif col[0] == ':':
            self._align_follow = tbase.Column.ALIGN_LEFT
        elif col[-1] == ':':
            self._align_follow = tbase.Column.ALIGN_RIGHT
        else:
            self._align_follow = None

    def min_len(self):
        return int(math.ceil(self.total_min_len() / self.colspan))

    def total_min_len(self):
        # ' :-: ' or ' :-- ' or ' --: ' or ' --- '
        return 5 + self.colspan - 1

    def render(self):
        total_col_len = self.col_len + (self.colspan - 1) + sum([col.col_len for col in self.pseudo_columns])
        total_col_len = total_col_len - (self.colspan - 1)

        if self._align_follow == tbase.Column.ALIGN_CENTER:
            lead = ':'
            trail = ':'
        elif self._align_follow == tbase.Column.ALIGN_LEFT:
            lead = ':'
            trail = '-'
        elif self._align_follow == tbase.Column.ALIGN_RIGHT:
            lead = '-'
            trail = ':'
        else:
            lead = '-'
            trail = '-'

        return ' ' + lead + '-' * (total_col_len - 4) + trail + ' '

    def align_follow(self):
        return self._align_follow


class MultiMarkdownAlignRow(tbase.Row):

    def new_empty_column(self):
        return MultiMarkdownAlignColumn(self, '-')

    def create_column(self, text):
        return MultiMarkdownAlignColumn(self, text)

    def is_header_separator(self):
        return True

    def is_separator(self):
        return True

    def is_align(self):
        return True


class MultiMarkdownTableParser(tbase.BaseTableParser):

    def _is_multi_markdown_align_row(self, str_cols):
        return self.columns_match_regex(str_cols, MultiMarkdownAlignColumn.PATTERN)

    def create_row(self, table, line):
        if self._is_multi_markdown_align_row(line.str_cols()):
            row = MultiMarkdownAlignRow(table)
        else:
            row = tbase.DataRow(table)
        return row

    def create_column(self, table, row, line_cell):
        column = tbase.BaseTableParser.create_column(self, table, row, line_cell)
        if len(line_cell.right_border_text) > 1:
            column.colspan = len(line_cell.right_border_text)
        return column


class MultiMarkdownTableDriver(tbase.TableDriver):

    def editor_insert_single_hline(self, table, table_pos):
        table.rows.insert(table_pos.row_num + 1, MultiMarkdownAlignRow(table))
        table.pack()
        return ("Single separator row inserted",
                tbase.TablePos(table_pos.row_num, table_pos.field_num))

    def editor_insert_hline_and_move(self, table, table_pos):
        table.rows.insert(table_pos.row_num + 1, MultiMarkdownAlignRow(table))
        table.pack()
        if table_pos.row_num + 2 < len(table):
            if table[table_pos.row_num + 2].is_separator():
                table.insert_empty_row(table_pos.row_num + 2)
        else:
            table.insert_empty_row(table_pos.row_num + 2)
        return("Single separator row inserted",
               tbase.TablePos(table_pos.row_num + 2, 0))
