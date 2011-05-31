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

import glob # not built-in, requires fnmatch also
import fnmatch # not built-in

import miso
from pyaosocket import AoImmediate

import tpytwink_utils as ut

def path_join(*args):
    # The os. routines, as they are implemented on top of Open C
    # functions, they expect and return UTF-8 encoded strings, while
    # internally we use the "unicode" type. Hence we must convert back
    # and forth.
    ll = [ut.to_str(arg) for arg in args if arg is not None]
    return ut.to_unicode(apply(os.path.join, ll))
    
def left_arrow_coordseq(area):
    tlx, tly, brx, bry = area
    return [(tlx,tly+(bry-tly)/2), (brx,tly), (brx,bry)]

def right_arrow_coordseq(area):
    tlx, tly, brx, bry = area
    return [(tlx,tly), (brx,tly+(bry-tly)/2), (tlx,bry)]

class Arrow:
    bg_color = 0xffffff
    border_color = 0
    fill_color = 0xffff00 # same as Recipient yellow
    
    def __init__(self, image, area, cs):
        self.image = image
        self.area = area

        #print repr(("arrow area", area))
        self.coordseq = cs(area)
        #print repr(("arrow seq", self.coordseq))

    def draw(self, avail):
        """
        avail:: Indicates whether the arrow should be "selectable".
        """
        self.clear() # to clear the whole rectangular widget area
        self.draw_arrow(avail)

    def draw_arrow(self, avail):
        fill = (avail and self.fill_color or self.bg_color)
        self.image.polygon(self.coordseq,
                           outline = self.border_color,
                           fill = fill)

    def clear(self):
        self.image.rectangle(self.area, fill = self.bg_color)

class PicFile:
    def __init__(self, path, fn, tn_width):
        # We want to have the image width encoded in the name, so that if
        # we should end up changing "tn_width", we know to have new
        # thumbnails generated.
        tn_dir = u"_galthumb_%d" % tn_width

        self.path = path
        self.fn = fn
        self.pn = self.path + u"\\" + self.fn

        self.tn_path = path + u"\\" + tn_dir
        # .txt here seems to be one of the few things we can use to
        # fool the recognizer so that the thumbnails are _not_
        # displayed in Gallery, which would involve generating
        # thumbnails for the thumbnails. And we do not want any
        # duplicates in the gallery.
        self.tn_pn = self.tn_path + u"\\" + fn + "thumb.txt"

        self.tn_fail = False
        self.tn_image = None

        self.image = None
        self.immediate = None

    def makedirs(self):
        try:
            os.makedirs(ut.to_str(self.tn_path))
        except:
            # Strangely throws an exception if the path already exists.
            pass

    def stop(self):
        """
        Stops any outstanding "create_tn_image" request processing.
        """
        if self.image:
            self.image.stop()
            self.image = None

        if self.tn_image:
            self.tn_image.stop()
            self.tn_image = None

        if self.immediate:
            self.immediate.close()
            self.immediate = None

    def _check_code(self, code):
        if code != 0:
            # A typical error would be -4, or KErrNoMemory.
            # Note that cannot raise a unicode object, hence the "str".
            raise ("failed to load image %s (%d)" % (str(self.fn), code))

    def _try(self, action):
        try:
            action()
        except:
            self.tn_fail = True
            self.image = self.tn_image = None
            ut.print_exception()
            self.cb("fail")
            return True
        return False

    def _imm_completed(self, code, user_cb):
        def action():
            self._check_code(code)
            user_cb()

        self._try(action)

    def _via_immediate(self, user_cb):
        if self.immediate:
            self.immediate.cancel()
        else:
            self.immediate = AoImmediate()
            self.immediate.open()
        self.immediate.complete(self._imm_completed, user_cb)

    def _saved(self, code):
        #print ["saved", code]

        def finish():
            self.cb("ok")
            self.tn_image = None # clear from cache

        def action():
            self._via_immediate(finish)

        self._try(action)

    def _resized(self, tn_image):
        #print ["resized", tn_image]

        self.tn_image = tn_image
        self.image = None

        def req_save():
            self.makedirs()
            self.tn_image.save(self.tn_pn, callback = self._saved, format = "JPEG")
        def action():
            # We pass to the caller already, but this does not yet
            # complete the request.
            self.cb(self.tn_image)

            self._via_immediate(req_save)

        self._try(action)

    def _loaded(self, code):
        #print ["loaded", code]

        def req_resize():
            #print "resizing %s" % repr(self.pn)
            #print "resizing %s" % repr(self.image)
            #print "resizing to %s" % repr(self.tn_size)
            self.image.resize(self.tn_size, keepaspect = 1,
                              callback = self._resized)
            #print "resize request made"

        def action():
            self._check_code(code)
            self._via_immediate(req_resize)

        self._try(action)
            
    def create_tn_image(self, tn_size, cb):
        #print "create tn"
        
        try:
            info = graphics.Image.inspect(self.pn)
            #print repr(info)
            img_size = info["size"]
            img = graphics.Image.new(img_size)
            self.tn_size = tn_size
            self.cb = cb
            img.load(self.pn, callback = self._loaded)
            self.image = img
        except:
            ut.print_exception()
            self.tn_fail = True
            raise # re-raise

    def get_tn_image(self):
        # This ought to be fast enough so that we can do without
        # asynch loading. Note that it is legal to blit even just
        # partially loaded images onto the screen, but that probably
        # will not be necessary here.
        return graphics.Image.open(self.tn_pn)

def list_images(root, mk_pic):
    def g(p):
        pn = path_join(root, p)
        res = []
        for fn in os.listdir(ut.to_str(pn)):
            fn = ut.to_unicode(fn)
            fnp = path_join(pn, fn)
            if os.path.isdir(ut.to_str(fnp)):
                if not fnmatch.fnmatch(fn, "_*"):
                    res.extend(g(path_join(p, fn)))
            elif os.path.isfile(ut.to_str(fnp)):
                if fnmatch.fnmatch(fn, "*.jpg"):
                    res.append(mk_pic(pn, fn))
        return res
    
    return g(None)

class DriveInfo:
    def __init__(self, drive, mk_pic):
        self.dir = drive + u"\\images"
        self.mk_pic = mk_pic
        self.dirty = True
        self.fs = miso.FsNotifyChange()
        self.filelist = []

    def fs_observe(self):
        self.fs.notify_change(1, self._dir_changed, self.dir)
        
    def _dir_changed(self, error):
        if error == 0:
            self.dirty = True

    def refresh(self):
        if not self.dirty:
            return
        if os.path.isdir(ut.to_str(self.dir)):
            self.filelist = list_images(self.dir, self.mk_pic)
        self.dirty = False
        self.fs_observe()
    
    def close(self):
        self.fs.close()

class FileList:
    def __init__(self, mk_pic):
        self.mk_pic = mk_pic
        self.drivelist = {} # (drive_name, DriveInfo)
        self.filelist = [] # of PicFile

    def length(self):
        return (len(self.filelist))

    def empty(self):
        return (len(self.filelist) == 0)

    def get(self, ix):
        return (self.filelist[ix])

    def refresh(self):
        """
        Returns True if the list changed as a result of the refresh,
        and False otherwise.
        """
        dirty = False
        for drive in e32.drive_list():
            if not self.drivelist.has_key(drive):
                self.drivelist[drive] = DriveInfo(drive, self.mk_pic)
                dirty = True
        for di in self.drivelist.itervalues():
            if di.dirty:
                di.refresh()
                dirty = True
        if dirty:
            self.filelist = []
            for di in self.drivelist.itervalues():
                self.filelist.extend(di.filelist)
        return dirty
    
    def close(self):
        for di in self.drivelist.itervalues():
            di.close()
    
class GalleryScreen:
    text_font = (None, 20, None)

    def __init__(self, image, redraw):
        self.image = image
        self.redraw = redraw
        self.dirty = False

        # Currently loading thumbnail (PicFile), if any.
        self.loading_tn = None

        # Called with None if user does a Cancel, and otherwise with
        # the selected PicFile.
        self.cb = lambda pic: None

        # We are defining a fixed image width here, to allow having to
        # generate two sets of thumbnails for cases where the display
        # rotates. Here we try to choose something that should fit
        # regardless of device and rotation.
        self.tn_width = (7 * min(self.image.size[0], self.image.size[1])) / 10

        self.compute_layout()
        
        mk_pic = lambda pn, fn: PicFile(pn, fn, self.tn_width)
        self.filelist = FileList(mk_pic)

    def compute_layout(self):
        """
        If "self.image" should be replaced with one of different
        dimensions, this method is to be called to compute the new
        layout.
        """
        self.area = (0, 0, self.image.size[0], self.image.size[1])

        tlx, tly, brx, bry = self.area
        #print repr(self.area)
        area_sz = ut.area_size(self.area)

        margin = 10
        
        fn_height = area_sz[1] / 5 - margin
        self.fn_area = (tlx, bry - fn_height, brx, bry)
        #print repr(self.fn_area)

        arrow_w = (area_sz[0] - self.tn_width) / 2
        arrow_size = (arrow_w - (2 * margin), arrow_w - (2 * margin))

        pic_tlx = tlx + arrow_w
        self.pic_space = (pic_tlx, tly,
                          pic_tlx + self.tn_width, bry - fn_height)
        #print repr((self.tn_width, self.pic_space))

        larr_space = (tlx, tly,
                      tlx + arrow_w, bry - fn_height)
        #print repr(larr_space)
        larr_area = ut.center_size_in_area(larr_space, arrow_size)
        #print repr(larr_area)
        self.left_arrow = Arrow(self.image, larr_area, left_arrow_coordseq)

        rarr_space = (brx - arrow_w, tly,
                      brx, bry - fn_height)
        #print repr(rarr_space)
        rarr_area = ut.center_size_in_area(rarr_space, arrow_size)
        #print repr(rarr_area)
        self.right_arrow = Arrow(self.image, rarr_area, right_arrow_coordseq)

    def draw_left_arrow(self):
        avail = (not self.filelist.empty())
        self.left_arrow.draw(avail)

    def draw_right_arrow(self):
        avail = (not self.filelist.empty())
        self.right_arrow.draw(avail)

    def draw_filename(self):
        self.clear_area(self.fn_area)
        if self.sel_ix != -1:
            picfile = self.filelist.get(self.sel_ix)
            ut.draw_text(self.image, self.fn_area,
                         picfile.fn,
                         font = self.text_font,
                         adj = ut.center,
                         margin = (5,5,5,5))

    def scan_files(self):
        self.filelist.refresh()
        self.sel_ix = -1
        #print repr([pic.pn for pic in self.filelist])
        if not self.filelist.empty():
            self.sel_ix = 0

    def draw_no_images(self):
        """
        Draws a "No images" indicator to the thumbnail area.
        """
        self.clear_area(self.pic_space)
        ut.draw_text(self.image, self.pic_space,
                     u"No images",
                     font = self.text_font,
                     adj = ut.center,
                     margin = (5,5,5,5))

    def draw_tn_image(self, tn_image):
        self.clear_area(self.pic_space)
        if tn_image:
            parea = ut.center_size_in_area(self.pic_space, tn_image.size)
            tgtoff = (parea[0], parea[1])
            self.image.blit(image = tn_image, target = tgtoff)
        self.redraw(self.pic_space)

    def draw_picture(self):
        self.draw_tn_later = False
        
        if self.sel_ix == -1:
            self.draw_no_images()
            return

        ix = self.sel_ix # needed for closure
        picfile = self.filelist.get(self.sel_ix)

        if picfile.tn_fail:
            self.draw_tn_image(None)
            return # cannot get the thumbnail
        
        pic_size = ut.area_size(self.pic_space)

        if picfile.tn_image:
            # Have thumbnail in memory.
            self.draw_tn_image(picfile.tn_image)
            return

        # Try to read a cached thumbnail from a file.
        try:
            tn = picfile.get_tn_image()
            self.draw_tn_image(tn)
            return
        except:
            pass

        self.draw_tn_image(None)

        # Maybe create a thumbnail and cache it.
        if not self.loading_tn:
            picfile.create_tn_image(pic_size, lambda stat: self._got_tn(ix, stat))
            self.loading_tn = picfile
        else:
            self.draw_tn_later = True

    def _got_tn(self, ix, tn):
        if tn == "ok" or tn == "fail":
            self.loading_tn.stop()
            self.loading_tn = None
            # We do not do opportunistic loading, i.e. we do not start
            # working say on the next already visited missing
            # thumbnail at this point. But if the currently shown
            # picture has no thumbnail yet, then we ought to get that
            # one.
            if tn == "ok" and self.draw_tn_later:
                self.draw_picture()
        elif self.sel_ix == ix:
            self.draw_tn_image(tn)

    def draw_all(self):
        self.draw_filename()
        self.draw_left_arrow()
        self.draw_right_arrow()
        self.draw_picture()

    def set_selected(self, nix):
        self.sel_ix = nix
        self.draw_filename()
        self.draw_picture()
        self.redraw(self.area)
    
    def select_prev(self):
        if self.sel_ix == -1:
            return
        nix = self.sel_ix - 1
        if nix < 0:
            nix = self.filelist.length() - 1
        self.set_selected(nix)

    def select_next(self):
        #print "next pic"
        if self.sel_ix == -1:
            return
        nix = self.sel_ix + 1
        if nix >= self.filelist.length():
            nix = 0
        self.set_selected(nix)

    def select_current(self):
        if self.sel_ix == -1:
            return
        self.cb(self.filelist.get(self.sel_ix))

    def event_cb(self, event):
        #print repr(["EVENT", event])
        if event["type"] == appuifw.EEventKey:
            code = event["keycode"]
            if code == key_codes.EKeyLeftArrow:
                self.select_prev()
            elif code == key_codes.EKeyRightArrow:
                self.select_next()
            elif code == key_codes.EKeySelect:
                self.select_current()

    def clear_area(self, area):
        self.image.rectangle(area, fill = 0xffffff)

    def clear(self):
        self.clear_area(self.area)

    def redraw_all(self):
        self.clear() # clear all
        self.draw_all()
        self.redraw(self.area) # redraw all

    def resize(self, image, is_active):
        self.image = image
        if is_active:
            self.compute_layout()
            self.redraw_all()
        else:
            self.dirty = True

    def activate(self):
        #print "gallery activated"
        if self.dirty:
            self.dirty = False
            self.compute_layout()
        self.scan_files()
        self.redraw_all()

    def disactivate(self):
        if self.loading_tn:
            self.loading_tn.stop()
            self.loading_tn = None
        #print "gallery disactivated"

    def close(self):
        self.disactivate()
        self.filelist.close()
