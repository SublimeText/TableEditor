# table_pandoc_syntax.py - Pandoc table syntax with alignment support

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


from __future__ import division, print_function

import re

try:
    from . import table_base as tbase
    from . import table_border_syntax as tborder
except ValueError:
    import table_base as tbase
    import table_border_syntax as tborder


def create_syntax(table_configuration=None):
    return PandocTableSyntax(table_configuration)


class PandocAlignColumn(tbase.Column):
    """Column class that handles pandoc grid table alignment."""

    def __init__(self, row, separator: str):
        tbase.Column.__init__(self, row)
        self.separator = separator
        self._parse_alignment(separator)

    def _parse_alignment(self, sep: str):
        """Parse alignment from separator string like ':===' or '==:' or ':=:'."""
        # Remove spaces and get the core separator
        core = sep.strip()

        if core.startswith(":") and core.endswith(":"):
            self._align_follow = tbase.Column.ALIGN_CENTER
        elif core.startswith(":"):
            self._align_follow = tbase.Column.ALIGN_LEFT
        elif core.endswith(":"):
            self._align_follow = tbase.Column.ALIGN_RIGHT
        else:
            self._align_follow = None

    def min_len(self):
        # Minimum is 3 characters like '---' or '==='
        return 3

    def render(self):
        # Get the base separator character (- or =)
        base_char = "=" if "=" in self.separator else "-"

        # Render based on alignment
        if self._align_follow == tbase.Column.ALIGN_CENTER:
            # Center: ':===:'
            if self.col_len <= 2:
                return base_char * self.col_len
            return ":" + base_char * (self.col_len - 2) + ":"
        elif self._align_follow == tbase.Column.ALIGN_LEFT:
            # Left: ':==='
            if self.col_len <= 1:
                return base_char * self.col_len
            return ":" + base_char * (self.col_len - 1)
        elif self._align_follow == tbase.Column.ALIGN_RIGHT:
            # Right: '===:'
            if self.col_len <= 1:
                return base_char * self.col_len
            return base_char * (self.col_len - 1) + ":"
        else:
            # No alignment: '===='
            return base_char * self.col_len

    def align_follow(self):
        return self._align_follow


class PandocAlignRow(tbase.Row):
    """Row class for pandoc grid table separators with alignment."""

    def __init__(self, table, separator="-"):
        tbase.Row.__init__(self, table)
        self.separator = separator
        self.align_columns = []

    def new_empty_column(self):
        return PandocAlignColumn(self, self.separator * 3)

    def create_column(self, text):
        return PandocAlignColumn(self, text)

    def is_header_separator(self):
        return True

    def is_separator(self):
        return True

    def is_align(self):
        return True

    def render(self):
        r = self.syntax.hline_out_border
        for ind, column in enumerate(self.columns):
            if ind != 0:
                r += self.syntax.hline_in_border
            r += column.render()
        r += self.syntax.hline_out_border
        return r


class PandocTableParser(tborder.BorderTableParser):
    """Enhanced parser that recognizes alignment in pandoc grid tables."""

    def _is_single_row_separator_with_align(self, str_cols):
        """Check if this is a separator row with possible alignment markers."""
        if len(str_cols) == 0:
            return False
        for col in str_cols:
            # Pattern allows for alignment colons at start/end
            if not re.match(r"^\s*:?[\-]+:?\s*$", col):
                return False
        return True

    def _is_double_row_separator_with_align(self, str_cols):
        """Check if this is a double separator row with possible alignment markers."""
        if len(str_cols) == 0:
            return False
        for col in str_cols:
            # Pattern allows for alignment colons at start/end
            if not re.match(r"^\s*:?[=]+:?\s*$", col):
                return False
        return True

    def _has_alignment_markers(self, str_cols):
        """Check if any column has alignment markers (colons)."""
        for col in str_cols:
            if ":" in col:
                return True
        return False

    def create_row(self, table, line):
        str_cols = line.str_cols()

        # Check for separator rows with alignment
        if self._is_single_row_separator_with_align(str_cols):
            if self._has_alignment_markers(str_cols):
                # Create alignment-aware separator row
                row = PandocAlignRow(table, "-")
                return row
            else:
                # Regular separator without alignment
                row = tborder.SeparatorRow(table, "-")
                return row
        elif self._is_double_row_separator_with_align(str_cols):
            if self._has_alignment_markers(str_cols):
                # Create alignment-aware double separator row
                row = PandocAlignRow(table, "=")
                return row
            else:
                # Regular double separator without alignment
                row = tborder.SeparatorRow(table, "=")
                return row
        else:
            # Regular data row
            row = self.create_data_row(table, line)
            return row

    def create_column(self, table, row, line_cell):
        """Create appropriate column based on row type."""
        if isinstance(row, PandocAlignRow):
            # For alignment rows, create alignment columns
            column = row.create_column(line_cell.text)
            column.left_border_text = line_cell.left_border_text
            column.right_border_text = line_cell.right_border_text
            return column
        else:
            # For other rows, use the default behavior
            return tborder.BorderTableParser.create_column(self, table, row, line_cell)


class PandocTableDriver(tborder.BorderTableDriver):
    """Enhanced driver for pandoc tables with alignment support."""

    def editor_insert_single_hline(self, table, table_pos):
        """Insert a single horizontal line, preserving alignment if present."""
        # Check if we should preserve alignment from existing rows
        has_alignment = False
        for row in table.rows:
            if isinstance(row, PandocAlignRow):
                has_alignment = True
                break

        if has_alignment:
            table.rows.insert(table_pos.row_num + 1, PandocAlignRow(table, "-"))
        else:
            table.rows.insert(table_pos.row_num + 1, tborder.SeparatorRow(table, "-"))

        table.pack()
        return (
            "Single separator row inserted",
            tbase.TablePos(table_pos.row_num, table_pos.field_num),
        )

    def editor_insert_double_hline(self, table, table_pos):
        """Insert a double horizontal line, preserving alignment if present."""
        # Check if we should preserve alignment from existing rows
        has_alignment = False
        for row in table.rows:
            if isinstance(row, PandocAlignRow):
                has_alignment = True
                break

        if has_alignment:
            table.rows.insert(table_pos.row_num + 1, PandocAlignRow(table, "="))
        else:
            table.rows.insert(table_pos.row_num + 1, tborder.SeparatorRow(table, "="))

        table.pack()
        return (
            "Double separator row inserted",
            tbase.TablePos(table_pos.row_num, table_pos.field_num),
        )


class PandocTableSyntax(tbase.TableSyntax):
    """Pandoc table syntax with alignment support."""

    def __init__(self, table_configuration):
        tbase.TableSyntax.__init__(self, "Pandoc", table_configuration)

        self.table_parser = PandocTableParser(self)
        self.table_driver = PandocTableDriver(self)

        self.hline_out_border = "+"
        self.hline_in_border = "+"
