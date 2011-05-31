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

class LogoScreen:
    text_height = 20
    text_font = (None, text_height, None)
    
    def __init__(self, image, redraw):
        self.redraw = redraw
        self.logo = graphics.Image.open(ut.app_drive + u"\\data\\tpytwink\\logo.png")
        
        self.text = u""
        self.dot_timer = e32.Ao_timer()

        self.dirty = False
        self.image = image
        self.select_action = None
        self.compute_layout()

    def compute_layout(self):
        self.area = (0, 0, self.image.size[0], self.image.size[1])

        spare_h = self.image.size[1] - self.logo.size[1] - self.text_height
        if spare_h < 0:
            spare_h = 0

        logo_h = self.logo.size[1] + spare_h / 2
        text_h = self.image.size[1] - logo_h
        
        self.text_area = (0, logo_h, self.image.size[0], self.image.size[1])

        logo_area_size = (self.image.size[0], logo_h)
        self.logo_off = ut.center(self.logo.size, logo_area_size)

    def draw_image(self):
        self.image.blit(image = self.logo, target = self.logo_off)

    def set_dot_timer(self):
        self.dot_timer.after(3, self._dot_timer_expired)

    def redraw_text(self):
        self.clear_area(self.text_area)
        self.draw_wait_text()
        self.redraw(self.text_area)

    def _dot_timer_expired(self):
        self.redraw_text()
        self.num_dots += 1
        if self.num_dots > 3:
            self.num_dots = 1
        self.set_dot_timer()

    def draw_wait_text(self):
        tx = self.text + (u"." * self.num_dots)
        ut.draw_text(self.image, self.text_area,
                     tx, font = self.text_font,
                     adj = ut.center, margin = (5,5,5,5))

    def clear_area(self, area):
        self.image.rectangle(area, fill = 0xffffff)

    def redraw_all(self):
        self.clear_area(self.area) # clear all
        self.draw_image()
        self.draw_wait_text()
        self.redraw(self.area) # redraw all

    def resize(self, image, is_active):
        self.image = image
        if is_active:
            self.compute_layout()
            self.redraw_all()
        else:
            self.dirty = True

    def activate(self):
        self.num_dots = 1
        if self.dirty:
            self.dirty = False
            self.compute_layout()
        self.redraw_all()
        self.set_dot_timer()

    def disactivate(self):
        self.dot_timer.cancel()

    def close(self):
        self.disactivate()

    def event_cb(self, event):
        #print repr(["EVENT", event])
        if event["type"] == appuifw.EEventKey:
            code = event["keycode"]
            if code == key_codes.EKeySelect:
                if self.select_action:
                    self.select_action()
