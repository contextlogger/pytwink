#
# Copyright 2007 Helsinki Institute for Information Technology (HIIT)
# and the authors.  All rights reserved.
#
# Authors: Tero Hasu <tero.hasu@hut.fi>
#

# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import appuifw
import e32
import graphics
import key_codes
import os

import tpytwink_utils as ut

# An abstract class for list elements.
class Cell:
    def __init__(self):
        self.bg_color = 0xffffff # white

    def set_geometry(self, image, area):
        """
        Invoked initially, and after a change to image area size or
        position. Subclassers may have to override if this operation
        involves recomputation of some of the internal state.
        """
        self.image = image
        self.area = area

    def is_selectable(self):
        return False

    def draw(self, is_selected):
        """
        The default behavior is to draw nothing but the background.
        Subclassers will probably want to override.
        """
        self.clear()

    def clear(self):
        self.image.rectangle(self.area, fill = self.bg_color)

    def draw_text(self, text, **kw):
        ut.draw_text(self.image, self.area, text, **kw)

class TitleCell(Cell):
    def __init__(self):
        Cell.__init__(self)
        self.font = (None, 20, graphics.FONT_BOLD)
    
    def draw(self, is_selected):
        self.clear()
        self.draw_text(u"TPYTWINK", adj = ut.center, font = self.font)

class MarginCell(Cell):
    cell_margin = (4,4,4,4)

    def __init__(self):
        Cell.__init__(self)
        self.cell_color = 0xdedede # grey
        self.hi_cell_color = 0xffff00 # yellow
        self.action = None

    def set_geometry(self, image, area):
        Cell.set_geometry(self, image, area)
        self.cell_area = ut.margin_to_area(self.area, self.cell_margin)
        
    def is_selectable(self):
        """
        If selectable, there is an action, an exactly one action.
        The control itself does not know whether selected or not.
        Selectability does not change; once selectable, always selectable.
        """
        return (self.action is not None)

    def draw(self, is_selected):
        self.clear()
        self.draw_cell(is_selected)
        self.draw_content()

    def draw_cell(self, is_selected):
        color = is_selected and self.hi_cell_color or self.cell_color
        self.image.rectangle(self.cell_area, fill = color)

    def draw_content(self):
        """
        For subclassers to override.
        """
        pass

class LabeledCell(MarginCell):
    label_row_height = 20

    def __init__(self):
        MarginCell.__init__(self)
        self.label_text = None
        self.label_font = (None, 18, None)
        self.label_color = 0x222222
        self.label_margin = (5, 5, 3, 2)

    def set_geometry(self, image, area):
        MarginCell.set_geometry(self, image, area)
        area = self.cell_area
        self.label_area = (area[0], area[1],
                           area[2], area[1] + self.label_row_height)
        self.content_area = (area[0], area[1] + self.label_row_height,
                             area[2], area[3])

    def draw_label(self):
        ut.draw_text(self.image, self.label_area, self.label_text,
                     font = self.label_font, fill = self.label_color,
                     adj = ut.vcenter, margin = self.label_margin)

    def draw_content(self):
        self.draw_label()
        self.draw_labeled_content()

    def draw_labeled_content(self):
        pass

class LabeledTextCell(LabeledCell):
    def __init__(self):
        LabeledCell.__init__(self)
        self.text = None
        self.text_margin = self.label_margin
        self.text_font = (None, 20, None)
        self.text_color = 0

    def draw_labeled_content(self):
        ut.draw_text(self.image, self.content_area, self.text,
                     font = self.text_font, fill = self.text_color,
                     adj = ut.vcenter, margin = self.text_margin)

def compact(xs):
    ys = []
    for x in xs:
        if x is not None:
            ys.append(x)
    return ys

def all_none(*xs):
    for x in xs:
        if x is not None:
            return False
    return True

def gui_address(m):
    title = m.get("title", None)
    first_name = m.get("first_name", None)
    second_name = m.get("second_name", None)
    last_name = m.get("last_name", None)
    email_address = m.get("email_address", None)
    if not all_none(first_name, second_name, last_name):
        return (u" ".join(compact([last_name and title or None, first_name, second_name, last_name])))
    elif email_address is not None:
        return unicode(email_address)
    else:
        return u""

class ListScreen:
    cell_order = ["title", "mood", "recipient", "picfile"]
    
    def __init__(self, image, redraw):
        self.image = image
        self.redraw = redraw
        self.dirty = False
        
        self.is_active = False
        self.create_cells()
        self.compute_layout()
        self.sel_ix = -1
        self.sel_cell = None

    def create_cells(self):
        self.cells = {}

        cell = TitleCell()
        self.cells["title"] = cell

        cell = LabeledTextCell()
        cell.label_text = u"Status/mood/activity:"
        self.cells["mood"] = cell
        self.set_mood(u"")

        cell = LabeledTextCell()
        cell.label_text = u"Recipient:"
        self.cells["recipient"] = cell
        self.set_recipient({})

        cell = LabeledTextCell()
        cell.label_text = u"Picture/avatar:"
        self.cells["picfile"] = cell
        self.set_picfile(None)

    def compute_layout(self):
        self.area = (0, 0, self.image.size[0], self.image.size[1])

        w, h = ut.area_size(self.area)
        h8 = h / 7
        tlx = tly = bry = 0
        brx = w

        ch = h8
        bry += ch
        self.cells["title"].set_geometry(self.image, (tlx, tly, brx, bry))
        tly += ch

        ch = 2 * h8
        bry += ch
        self.cells["mood"].set_geometry(self.image, (tlx, tly, brx, bry))
        tly += ch

        ch = 2 * h8
        bry += ch
        self.cells["recipient"].set_geometry(self.image, (tlx, tly, brx, bry))
        tly += ch

        ch = 2 * h8
        bry += ch
        self.cells["picfile"].set_geometry(self.image, (tlx, tly, brx, bry))
        tly += ch

    def set_mood(self, text):
        cell = self.cells["mood"]
        cell.text = text
        self.refresh_cells(cell)

    def set_recipient(self, recipient):
        cell = self.cells["recipient"]
        cell.text = (recipient == {}) and u"[ADD]" or gui_address(recipient)
        self.refresh_cells(cell)

    def set_picfile(self, picfile):
        cell = self.cells["picfile"]
        cell.text = (picfile is None) and u"[ADD]" or ut.basename(picfile)
        self.refresh_cells(cell)

    def set_mood_action(self, cb):
        self.cells["mood"].action = cb

    def set_recipient_action(self, cb):
        self.cells["recipient"].action = cb

    def set_picfile_action(self, cb):
        self.cells["picfile"].action = cb

    def _draw_cell(self, cell):
        cell.draw(cell is self.sel_cell)

    def _draw_all_cells(self):
        for cell in self.cells.itervalues():
            self._draw_cell(cell)

    def refresh_cells(self, *cells):
        if not self.is_active: return
        for cell in cells:
            if cell is not None:
                self._draw_cell(cell)
        self.redraw(self.area) # redraw all

    def refresh_all_cells(self):
        if not self.is_active: return
        self._draw_all_cells()
        self.redraw(self.area) # redraw all
        
    def select_prev(self):
        nix = self.sel_ix
        while nix > 0:
            nix -= 1
            name = self.cell_order[nix]
            cell = self.cells[name]
            if cell.is_selectable():
                oldcell = self.sel_cell
                self.sel_ix = nix
                self.sel_cell = cell
                self.refresh_cells(oldcell, cell)
                return

    def select_next(self):
        limit = len(self.cell_order) - 1
        nix = self.sel_ix
        while nix < limit:
            nix += 1
            name = self.cell_order[nix]
            cell = self.cells[name]
            if cell.is_selectable():
                oldcell = self.sel_cell
                self.sel_ix = nix
                self.sel_cell = cell
                self.refresh_cells(oldcell, cell)
                return

    def exec_cell_action(self):
        if self.sel_cell.action is not None:
            self.sel_cell.action()

    def event_cb(self, event):
        #print repr(["EVENT", event])
        if event["type"] == appuifw.EEventKey:
            code = event["keycode"]
            if code == key_codes.EKeyUpArrow:
                self.select_prev()
            elif code == key_codes.EKeyDownArrow:
                self.select_next()
            elif code == key_codes.EKeySelect:
                self.exec_cell_action()

    def clear(self):
        self.image.rectangle(self.area, fill = 0xffffff)

    def redraw_all(self):
        self.clear() # clear all
        self.refresh_all_cells()
        
    def resize(self, image, is_active):
        self.image = image
        if is_active:
            self.compute_layout()
            self.redraw_all()
        else:
            self.dirty = True

    def activate(self):
        self.is_active = True
        if self.dirty:
            self.dirty = False
            self.compute_layout()
        if self.sel_ix == -1:
            # First activation.
            self.select_next()
        self.redraw_all()

    def disactivate(self):
        if self.is_active:
            self.is_active = False
            ut.maybe_call_cb(self, "disactivate_cb")

    def close(self):
        self.disactivate()
