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

from tpytwink_logo_screen import LogoScreen
from tpytwink_list_screen import ListScreen
from tpytwink_gallery_screen import GalleryScreen
from tpytwink_engine import Engine
import tpytwink_utils as ut

def try_switch_bt_on():
    try:
        import pybtswitch
        if not pybtswitch.get_power_state():
            pybtswitch.set_power_state(1)
    except:
        pass

# "normal", "large", or "full"
appuifw.app.screen = 'large'

def choose_execute_action(strings, actions):
    index = appuifw.popup_menu(strings, u'Select action')
    if index is not None:
        actions[index]()

class App:
    """
    This is the controller that owns the engine and chooses which view
    should be displayed and when.
    """
    egg_list = [57, 53, 49] # keys 9, 5, 1

    def __init__(self, engine):
        self.image = None
        self.mode = None # {None, "filedata", "mood", "gallery", "send"}
        self.mode_cleanup = None
        self.screen = None
        self.logo_screen = None
        self.list_screen = None
        self.gallery_screen = None
        self.screen_list = []

        self.engine = engine
        self.engine.card.cb = self._card_cb
        
        self.lock = e32.Ao_lock()
        self.main_title = u"Tpytwink"
        self.old_title = appuifw.app.title

        self.egg_zero()

        appuifw.app.title = self.main_title
        appuifw.app.exit_key_handler = self.abort
        self.set_menu_items()

        self.set_up_canvas()

        self.image = graphics.Image.new(self.canvas.size)

        # This screen does not reflect what is in the model. It is
        # displayed when we want it to be, and displays whatever
        # situation aware wait text we want it to display.
        self.logo_screen = LogoScreen(self.image, self.redraw_cb)

        # This screen directly reflects the model, and can also be
        # used to edit the model.
        self.list_screen = ListScreen(self.image, self.redraw_cb)
        self.list_screen.set_mood_action(self._mood_select)
        self.list_screen.set_recipient_action(self._recipient_select)
        self.list_screen.set_picfile_action(self._picfile_select)

        self.gallery_screen = GalleryScreen(self.image, self.redraw_cb)
        self.gallery_screen.cb = self._gallery_done

        self.screen_list = [self.logo_screen, self.list_screen,
                            self.gallery_screen]

        self._card_cb("all")

    # --------------------------------------------------------------------
    # canvas
    
    def set_up_canvas(self):
        # We get cyclic references with these arguments.
        self.canvas = None
        self.canvas = appuifw.Canvas(self.redraw_cb,
                                     self.event_cb,
                                     self.resize_cb)
        appuifw.app.body = self.canvas

    def clear_canvas(self):
        appuifw.app.body = self.canvas = None

    def without_canvas(self, f):
        """
        The interaction between a Canvas and an "abnormal" sized
        screen appears to mess up dialogs somewhat; using this is a
        workaround.
        """
        self.clear_canvas()
        appuifw.app.screen = 'normal'
        try:
            f()
        finally:
            appuifw.app.screen = 'large'
            self.set_up_canvas()

    # --------------------------------------------------------------------
    # mood mode actions
    
    def _mood_select(self):
        new_value = appuifw.query(u"Status:", "text", self.engine.card.mood)
        if new_value is not None:
            self.engine.card.set_mood(new_value)
        
    def _recipient_select(self):
        strings = [u"Make public",
                   u"Keep private"]
        actions = [self.engine.set_public_recipient,
                   self.engine.set_private_recipient]
        choose_execute_action(strings, actions)

    def _picfile_select(self):
        strings = [u"Choose from Gallery",
                   u"Take new photo",
                   u"Remove picture"]
        actions = [self.to_gallery_mode,
                   self.engine.take_photo,
                   self.engine.card.remove_picfile]
        if self.engine.card.picfile is not None:
            strings = [u"View picture", u"Rename picture"] + strings
            actions = [self.engine.show_picfile,
                       self.engine.rename_picfile] + actions
        choose_execute_action(strings, actions)

    # --------------------------------------------------------------------
    # gallery mode actions
    
    def _gallery_done(self, picfile):
        """
        picfile:: None if nothing selected.
        """
        if picfile is not None:
            self.engine.card.set_picfile(picfile.pn)
        self.to_mood_mode()

    # --------------------------------------------------------------------
    # menu actions
    
    def send_card_cond(self):
        if self.engine.is_ready_to_send():
            if self.engine.config.get_store_on():
                strings = [u"Store card now", u"Do not store yet"]
            else:
                strings = [u"Send card now", u"Do not send yet"]
            actions = [self.to_send_mode, lambda: None]
            choose_execute_action(strings, actions)

    def edit_recipient(self):
        self.without_canvas(self.engine.edit_recipient)

    def toggle_debug_mode(self):
        self.engine.toggle_debug_on()
        self.set_menu_items()

    # --------------------------------------------------------------------
    # sending
    
    def _send_status(self, tp, text):
        if tp == "progress":
            self.logo_screen.text = text
            self.logo_screen.redraw_text()
        elif tp == "ok":
            appuifw.note(text, "info")
            self.engine.card.clear_temporary()
            self.to_filedata_mode()
        else: # fail
            appuifw.note(text, "error")
            self.engine.card.clear_temporary()
            self.to_filedata_mode()
    
    def _card_cb(self, field):
        # Here we must update the relevant properties of all the
        # screens that may be affected, if they do already exist.
        # However, only any visible screen may be redrawn.
        if self.list_screen is not None:
            if field == "mood" or field == "all":
                self.list_screen.set_mood(self.engine.card.mood)
            if field == "recipient" or field == "all":
                self.list_screen.set_recipient(self.engine.card.recipient)
            if field == "picfile" or field == "all":
                self.list_screen.set_picfile(self.engine.card.picfile)

    def clear_ap(self):
        self.engine.config.set_apid(False)
        appuifw.note(u"AP cleared", "info")

    # --------------------------------------------------------------------
    # scanning
    
    def set_gps_scan(self, value):
        is_on = self.engine.get_gps_scan()
        if is_on != value:
            self.engine.set_gps_scan(value)
            self.set_menu_items()

    def set_btprox_scan(self, value):
        is_on = self.engine.config.get_btprox_scan()
        if is_on != value:
            self.engine.config.set_btprox_scan(value)
            self.set_menu_items()

    def set_store_on(self, value):
        is_on = self.engine.config.get_store_on()
        if is_on != value:
            self.engine.config.set_store_on(value)
            self.set_menu_items()

    # --------------------------------------------------------------------
    # external commands
    
    def ensure_have_valid_sender(self):
        """
        Sender info is required, so failure is not an option here.
        """
        if self.engine.card.has_valid_sender():
            return
        def f():
            ch = appuifw.selection_list([u"Specify sender manually",
                                         u"Choose from Contacts"])
            if ch == 1:
                self.engine.select_sender()
            elif ch == 0:
                self.engine.edit_sender()
            if not self.engine.card.has_valid_sender():
                raise "sender must be set up to use this application"
        self.without_canvas(f)

    # --------------------------------------------------------------------
    # mode switching

    def to_mode(self, mode):
        if mode == self.mode:
            return

        if mode == "filedata" or mode == "send":
            screen = self.logo_screen
        elif mode == "mood":
            screen = self.list_screen
        elif mode == "gallery":
            screen = self.gallery_screen
        else:
            raise "assertion failure"

        if self.mode:
            if self.mode_cleanup:
                self.mode_cleanup()
                self.mode_cleanup = None

        self.mode = mode
        self.to_screen(screen)
        self.set_menu_items()
    
    def to_screen(self, screen):
        if screen is not self.screen:
            if self.screen is not None:
                self.screen.disactivate()
            self.screen = screen
            if self.screen is not None:
                self.screen.activate()

    def set_menu_items(self):
        main_menu = []
        if self.mode == "filedata":
            main_menu.append((u"Edit status", self.to_mood_mode))
        if self.mode == "filedata" or self.mode == "mood":
            if self.engine.config.get_store_on():
                main_menu.append((u"Store without file data", self.send_card_cond))
            else:
                main_menu.append((u"Send without file data", self.send_card_cond))
        if self.engine.get_gps_scan():
            toggle_gps_scan = (u"GPS scanning off",
                               lambda: self.set_gps_scan(False))
        else:
            toggle_gps_scan = (u"GPS scanning on",
                               lambda: self.set_gps_scan(True))
        if self.engine.config.get_btprox_scan():
            toggle_btprox_scan = (u"BT scanning off",
                                  lambda: self.set_btprox_scan(False))
        else:
            toggle_btprox_scan = (u"BT scanning on",
                                  lambda: self.set_btprox_scan(True))
        if self.engine.config.get_store_on():
            toggle_store_on = (u"Card sending on",
                               lambda: self.set_store_on(False))
        else:
            toggle_store_on = (u"Card storing on",
                               lambda: self.set_store_on(True))
        main_menu.extend([
            (u"View GPS", lambda: self.without_canvas(self.engine.show_gps)),
            (u"GPS config", self.engine.edit_gps_config),
            toggle_gps_scan,
            toggle_btprox_scan,
            (u"Change access point", self.engine.config.change_apid),
            toggle_store_on
            ])
        if self.engine.get_debug_on():
            main_menu.extend([
                (u"View GSM", lambda: self.without_canvas(self.engine.show_gsm)),
                (u"View BT", lambda: self.without_canvas(self.engine.show_btprox)),
                (u"Logo screen", lambda: self.to_screen(self.logo_screen)),
                (u"List screen", lambda: self.to_screen(self.list_screen)),
                (u"Gallery screen", lambda: self.to_screen(self.gallery_screen)),
                (u"View log", self.engine.show_log_file),
                (u"Choose recipient", lambda: self.without_canvas(self.engine.select_recipient)),
                (u"Edit recipient", self.edit_recipient),
                (u"Remove recipient", self.engine.remove_recipient),
                (u"Choose sender", lambda: self.without_canvas(self.engine.select_sender)),
                (u"Edit sender", lambda: self.without_canvas(self.engine.edit_sender)),
                (u"Remove sender", self.engine.remove_sender),
                (u"Remove context", self.engine.card.clear_context),
                (u"Remove access point", self.clear_ap),
                (u"Toggle scanning", self.engine.config.toggle_noscan),
                (u"Select Camera UID", self.engine.select_camera_uid)
                ])
        main_menu.append((u"Exit Tpytwink", self.abort))
        appuifw.app.menu = main_menu

    def to_filedata_mode(self):
        """
        To avoid surprises to the user, we only acquire when the
        acquisition screen is showing, and not at other times.
        """
        self.logo_screen.text = u"Waiting for file data"
        self.logo_screen.select_action = self.to_mood_mode
        self.to_mode("filedata")
        self.mode_cleanup = self.engine.stop_observing_filedata
        self.engine.start_observing_filedata(self._filedata_done)

    def to_mood_mode(self):
        self.to_mode("mood")
        ut.set_right_softkey_text(u"Back")
        def cleanup():
            appuifw.app.exit_key_handler = self.abort
            ut.set_right_softkey_text(u"Exit")
        def done():
            self.acquire_new_filedata()
        self.list_screen.disactivate_cb = cleanup
        appuifw.app.exit_key_handler = done
        self.mode_cleanup = cleanup

    def to_gallery_mode(self):
        self.to_mode("gallery")
        appuifw.app.exit_key_handler = lambda: self._gallery_done(None)
        ut.set_right_softkey_text(u"Close")
        def cleanup():
            ut.set_right_softkey_text(u"Exit")
        self.mode_cleanup = cleanup

    def to_send_mode(self):
        self.logo_screen.text = u""
        self.logo_screen.select_action = None
        self.to_mode("send")
        self.engine.send_card(self._send_status)
                
    # --------------------------------------------------------------------
    # filedata acquisition

    def acquire_new_filedata(self):
        self.engine.card.remove_filedata()
        self.to_filedata_mode()

    def _filedata_done(self):
        """
        Called when got the filedata.
        """
        if self.engine.is_ready_to_send():
            self.to_send_mode()
        else:
            self.acquire_new_filedata()

    # --------------------------------------------------------------------
    # general screen callbacks

    def redraw_cb(self, area):
        """
        The argument is a tuple of the form (tlx, tly, brx, bry),
        giving the area to redraw.
        """
        #print repr(["REDRAW", area])

        if self.canvas is None:
            return

        if self.image is None:
            self.canvas.rectangle(area, fill = 0xffffff)
            return

        tgtoff = (area[0], area[1])
        #print "target %s source %s" % (repr(tgtoff), repr(area))
        
        # Note that the docs are wrong, actually target = (tlx,tly),
        # and source = (tlx,tly,brx,bry).
        self.canvas.blit(image = self.image,
                         target = tgtoff,
                         source = area)

    def event_cb(self, event):
        #print repr(["EVENT", event])

        if event["type"] == appuifw.EEventKey:
            code = event["keycode"]
            egg_code = self.egg_input.pop()
            if code == egg_code:
                if len(self.egg_input) == 0:
                    self.toggle_debug_mode()
                    self.egg_zero()
                return
            else:
                self.egg_zero()
                
        if self.screen is not None:
            ut.allow_attr_error(lambda: self.screen.event_cb(event))

    def egg_zero(self):
        self.egg_input = ([] + self.egg_list)
        self.egg_input.reverse()

    def resize_cb(self, sz):
        """
        We get one of these events at startup, and one whenever the
        canvas is resized. And maybe some spurious ones as well.
        """
        #print repr(["RESIZE", sz])
        if self.canvas:
            self.image = graphics.Image.new(self.canvas.size)
            for screen in self.screen_list:
                screen.resize(self.image, self.screen == screen)

    # --------------------------------------------------------------------

    def abort(self):
        self.lock.signal()

    def loop(self):
        self.lock.wait()

    def close(self):
        self.screen = None
        self.logo_screen.close()
        self.list_screen.close()
        self.gallery_screen.close()

        # Kills the canvas (which may be somehow visible even when not
        # set as app.body, it seems) if this is the last reference.
        # Canvas still has references to self, but not the other way
        # around any longer, so it should get freed.
        self.canvas = None

        if not self.engine.get_debug_on():
            # The effect is not immediate, but rather concerns the
            # point where execution falls back to the framework.
            appuifw.app.set_exit()

        appuifw.app.menu = []
        appuifw.app.body = None
        appuifw.app.exit_key_handler = None
        appuifw.app.title = self.old_title

def run_app():
    try_switch_bt_on()
    
    # Keeping the engine and the GUI separate makes it easier to
    # ensure proper cleanup.
    engine = Engine()
    try:
        app = App(engine)
        try:
            app.ensure_have_valid_sender()
            #appuifw.note(u"Press Options to edit status", "info")
            app.to_filedata_mode()
            #app.to_screen(app.gallery_screen) 
            app.loop()
        finally:
            app.close()
    finally:
        engine.close()

def main():
    orig_exit_key_handler = appuifw.app.exit_key_handler

    appuifw.app.menu = []

    restart = None

    def run():
        try:
            try:
                run_app()
            finally:
                appuifw.app.exit_key_handler = orig_exit_key_handler
                appuifw.app.title = u'Console'
                appuifw.app.screen = 'normal'
                if ut.get_debug_on():
                    appuifw.app.body = ut.app_console.text
                appuifw.app.menu = [(u"Restart", restart)]
        except:
            ut.ensure_console()
            appuifw.app.body = ut.app_console.text
            import traceback
            traceback.print_exc()

    restart = run
    run()

if __name__ == '__main__':
    main()
