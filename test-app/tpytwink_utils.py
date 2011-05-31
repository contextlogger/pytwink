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
import os
import sys
import pytwink

debug_on = False
app_console = None

def report(x):
    pass

def get_debug_on():
    return debug_on

def ensure_console():
    global app_console
    if app_console is None:
        import series60_console
        app_console = series60_console.Console()
        sys.stderr = sys.stdout = app_console

def set_debug_on(on):
    """
    For faster and prettier startup, we do not create a console, and
    do not make it visible until debugging is turned on. This is a bit
    of a problem, though, if there is an error during initialization,
    but it is quite possible to set up the console in an exception
    handler if need be.
    """
    global debug_on
    global report
    if on == debug_on:
        return
    debug_on = on
    if on:
        ensure_console()
        def report(x):
            print(x)
    else:
        def report(x):
            pass

def set_right_softkey_text(text):
    pytwink.set_softkey_text(3009, text) # EAknSoftkeyExit

def allow_attr_error(f):
    try:
        f()
    except AttributeError:
        pass

def maybe_call_cb(obj, name):
    cb = getattr(obj, name, None)
    if cb:
        cb()

def to_unicode(s):
    if type(s) is unicode:
        return s
    return s.decode("utf-8")

def to_str(s):
    if type(s) is str:
        return s
    return s.encode("utf-8")

app_path = to_unicode(os.path.split(to_str(appuifw.app.full_name()))[0])
app_drive = app_path[:2]

def print_exception():
    import traceback
    traceback.print_exception(*sys.exc_info())

def dirname(fn):
    return to_unicode(os.path.dirname(to_str(fn)))

def basename(fn):
    # This will work also for an "fn" that already is just a basename,
    # and this is a way to avoid converting to str and back.
    return fn.split("\\")[-1]

def show_doc(fname):
    doc_lock = e32.Ao_lock()
    ch = appuifw.Content_handler(doc_lock.signal)
    ch.open(fname)
    doc_lock.wait()

def show_log(logdir):
    try:
        flist = [ to_unicode(fn)
                  for fn
                  in os.listdir(to_str(logdir))
                  if file.endswith(".txt") ]
    except:
        # The directory not existing will cause an exception that
        # appears to be quietly consumed, i.e., it is not printed
        # to the console.
        flist = []

    if len(flist) == 0:
        appuifw.note(u"No logs to display", "info")
        return

    index = appuifw.popup_menu(flist, u'Select file to view')
    if index is None:
        return
    fname = logdir + flist[index]

    show_doc(fname)

def center(objsz, canvassz):
    ow, oh = objsz
    cw, ch = canvassz
    return ((cw - ow) / 2, (ch - oh) / 2)

def vcenter(objsz, canvassz):
    ow, oh = objsz
    cw, ch = canvassz
    return (0, (ch - oh) / 2)

def center_high(objsz, canvassz):
    ow, oh = objsz
    cw, ch = canvassz
    return ((cw - ow) / 2, (ch - oh) / 3)

def center_size_in_area(area, size):
    #print repr(("center", area, size))
    asize = area_size(area)
    csize = center(size, asize) # gives adjustment
    tlx = area[0] + csize[0]
    tly = area[1] + csize[1]
    return (tlx,
            tly,
            tlx + size[0],
            tly + size[1])

def area_width(area):
    return area[2] - area[0]

def area_size(area):
    return (area[2] - area[0], area[3] - area[1])

def margin_to_area(area, margin):
    left, right, top, bottom = margin
    return (area[0] + left,
            area[1] + top,
            area[2] - right,
            area[3] - bottom)

def draw_text(image, area, text,
              font = None, fill = 0, adj = None, margin = None):
    """
    An uber-routine for drawing text.
    adj:: text_size -> area_size -> (x_adjustment, y_adjustment)
    margin:: (left, right, top, bottom)
    """
    if margin is not None:
        area = margin_to_area(area, margin)
    
    maxwidth = area_width(area)
    # get something like ((0,-16,59,0),60,6)
    m = image.measure_text(text, font = font, maxwidth = maxwidth)

    numchars = m[2]
    text = text[:numchars]

    tlx, tly, brx, bry = m[0]
    tw = brx - tlx
    th = bry - tly
    tsize = (tw, th)

    if adj is None:
        tpos = (area[0] - tlx, area[1] - tly)
    else:
        tadj = adj(tsize, area_size(area))
        tpos = (area[0] - tlx + tadj[0], area[1] - tly + tadj[1])
    
    image.text(tpos, text, font = font, fill = fill)

def text_size(image, text, font = None):
    m = image.measure_text(text, font = font)
    tlx, tly, brx, bry = m[0]
    tw = brx - tlx
    th = bry - tly
    tsize = (tw, th)
    return tsize

