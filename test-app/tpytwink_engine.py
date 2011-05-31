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

import sys
import appuifw
import time
import e32
import os
import simplejson
import pyinbox
import location
import pynewfile
import key_codes
import binascii
from pyaosocket import AoSocketServ, AoSocket, AoResolver
from pyaosocket import AoConnection
from pyaosocket import AoImmediate
import socket
import globalui
import contacts

import tpytwink_utils as ut

test_picfile = u"e:\\data\\%s.jpg" % "H\xe4h\xe4\xe4".decode("latin1")
test_filedata = u"e:\\data\\document.doc"

def my_select_access_point():
    ap_list = socket.access_points()
    names = [ unicode(m["name"]) for m in ap_list ]
    index = appuifw.popup_menu(names, u'Select AP')
    if index is None:
        return None
    return ap_list[index]["iapid"]

try:
    import positioning
    # "After successfully establishing an RPositioner sub-session, the
    # client application must call RPositioner::SetRequestor to identify
    # itself and (if appropriate) on who's behalf it is retrieving the
    # location information."
    positioning.set_requestors([{"type": "service",
                                 "format": "application",
                                 "data": "Tpytwink"}])
    gps_avail = True
except:
    gps_avail = False

def unirepr(x):
    return unicode(repr(x))

def mkdir_p(path):
    try:
        os.makedirs(path)
    except:
        # Strangely throws an exception if the path already exists.
        pass

def make_file(file, data):
    mkdir_p(os.path.dirname(file))
    fp = open(file, "w")
    try:
        fp.write(data)
    finally:
        fp.close()

class GpsScanner:
    """
    This is an "active" position scanner that, once started, runs on
    the background until you tell it to stop. It reports any events
    via callbacks.
    
    We will add a menu option that allows the user to choose the
    positioning module to use in this application. The setting will be
    persistent. If no such setting has been made, the system default
    shall be used.
    """
    
    def __init__(self, cb, module_id):
        self.cb = cb
        self.active = False
        self.module_id = (module_id or positioning.default_module())
        self.use_module(self.module_id)

    def use_module(self, module_id):
        if module_id is None: raise "must specify valid module ID"
        if self.module_id != module_id:
            isact = self.active
            if isact:
                self.stop()
            try:
                positioning.select_module(module_id)
                self.module_id = module_id
                ut.report("selected GPS module %d (%s)" % (self.module_id, self.module_gui_name()))
            finally:
                if isact:
                    self.start()

    def choose_module(self):
        """
        You may use this method to select another positioning module
        to use. The ID of the selected module is returned, or None if
        no selection was made. Use "use_module" to try and take the
        selected module into use.
        """
        mlist = [ m for m in positioning.modules() if m["available"] ]
        names = [ unicode(m["name"]) for m in mlist ]
        index = appuifw.popup_menu(names, u'Select technology')
        if index is None:
            return None
        tech = mlist[index]
        module_id = tech["id"]
        return module_id

    def module_gui_name(self):
        return positioning.module_info(self.module_id)["name"]

    def start(self):
        if self.active:
            return
        positioning.position(course = 1, satellites = 1,
                             callback = self._cb,
                             interval = 30000000,
                             partial = 0)
        self.active = True

    def _cb(self, event):
        self.cb(event)

    def stop(self):
        if self.active:
            positioning.stop_position()
            self.active = False

    def close(self):
        self.stop()

def get_gsm():
    try:
        gsm = location.gsm_location()
    except:
        gsm = None
    return gsm

class GsmScanner:
    def __init__(self):
        self.immediate = AoImmediate()
        self.immediate.open()

    def close(self):
        self.immediate.close()

    def cancel(self):
        self.immediate.cancel()

    def scan(self, user_cb):
        """
        user_cb:: A callable that takes one argument, namely the GSM
                  cell ID data.
        """
        self.gsm = get_gsm()
        self.immediate.complete(self._imm_completed, user_cb)

    def _imm_completed(self, code, user_cb):
        user_cb(self.gsm)

def add_colons(s):
    s = str(s)
    return s[0:2] + ":" + s[2:4] + ":" + s[4:6] + ":" + \
           s[6:8] + ":" + s[8:10] + ":" + s[10:12]

class BtproxScanner:
    def __init__(self):
        self.timer = e32.Ao_timer()
        self.resolver = AoResolver()
        self.resolver.open()
        self.active = False

    def scan(self, cb):
        if self.active:
            self.cancel()
        self.cb = cb
        self.list = []
        self.resolver.discover(self._cb, None)
        self.timer.after(25, self._timeout)
        self.active = True

    def _timeout(self):
        """
        We use a timer to restrict the scan duration to something
        reasonable.
        """
        self.active = False
        ut.report("btprox scan timeout")
        self.resolver.cancel()
        self.cb(self.list) # anything so far

    def _cb(self, error, mac, name, dummy):
        ut.report([error, mac, name, dummy])
        self.active = False
        if error == -25: # KErrEof (no more devices)
            self.timer.cancel()
            self.cb(self.list)
        elif error:
            self.timer.cancel()
            ut.report("BT scan error %d" % error)
            appuifw.note(u"Bluetooth scan failed", "error")
            self.cb(None)
        else:
            self.list.append({"mac": add_colons(mac), "name": name})
            self.resolver.next()
            self.active = True

    def cancel(self):
        self.resolver.cancel()
        self.timer.cancel()
        self.active = False

    def close(self):
        self.cancel()
        self.resolver.close()

class Value:
    def __init__(self, value):
        self.value = value

class PublishContact:
    title = u"Make public"
    email_address = u"publish@myhost.mydomain"
    is_group = False

    def find(self, name):
        if name == "email_address":
            return [Value(self.email_address)]
        elif name == "first_name":
            return [Value(self.title)]
        else:
            return []

public_recipient = {"first_name": u"Make public",
                    "email_address": u"publish@myhost.mydomain"}

private_recipient = {"first_name": u"Keep private",
                     "email_address": u"private@myhost.mydomain"}

def select_contact(with_publish):
    db = contacts.open()

    clist = [ c for c
              in [ db[cid] for cid in db ]
              if (not c.is_group) and (c.find("email_address") != []) ]

    if with_publish:
        clist = [PublishContact()] + clist
    else:
        if clist == []:
            appuifw.note(u"No contacts to select", "error")
            return None

    chlist = [ unicode(c.title) for c in clist ]
    index = appuifw.popup_menu(chlist, u'Select contact')
    if index is None:
        return None

    chentry = clist[index]
    cmap = {}

    def get_value(name):
        fields = chentry.find(name)
        if len(fields) > 0:
            cmap[name] = fields[0].value
    
    fields = chentry.find("email_address")
    if len(fields) == 1:
        cmap["email_address"] = fields[0].value
    elif len(fields) > 1:
        chlist = [ unicode(f.value) for f in fields ]
        index = appuifw.popup_menu(chlist, u'Select address')
        if index is None:
            return None
        cmap["email_address"] = fields[index].value
    else:
        raise "assertion failure"

    get_value("first_name")
    get_value("last_name")
    get_value("first_name_reading")
    get_value("last_name_reading")
    get_value("second_name")

    return cmap

def read_file(fname):
    # This is not common knowledge, but on Symbian you can pass a
    # UTF-8 encoded filename to fopen (C function), and this appears
    # to work with Python as well.
    fp = open(fname.encode("utf-8"), "r")
    try:
        return fp.read()
    finally:
        fp.close()

dest_info = ("myhost.mydomain", 80, "/upload.php")

def filename_str_encode(s):
    # see http://www.faqs.org/rfcs/rfc1867.html

    try:
        es = s.encode("ascii")
        if es.find('"') == -1:
            return '"' + es + '"'
    except UnicodeError:
        pass
    
    # see http://www.faqs.org/rfcs/rfc1522.html
    es = binascii.b2a_qp(s.encode("utf-8"), True, True)
    return ("=?UTF-8?Q?%s?=" % es)

INFINITY = float('1e66666')

def is_nan(o):
    return (o != o) or (o == INFINITY) or (o == -INFINITY)

def filter_nan(d):
    new_d = {}
    for k, v in d.iteritems():
        if type(v) == dict:
            new_d[k] = filter_nan(v)
        elif is_nan(v):
            pass
        else:
            new_d[k] = v
    return new_d

def serialize_card(card):
    """
    We might consider making card sending more memory friendly by
    building the serialized form as it is required. In particular,
    reading the photo from a file in small chunks without storing the
    whole thing in memory would be useful. We could use a generator
    function, possibly, so that the sending function would repeatedly
    invoke the generator as it should require more data to send.
    """
    host, port, path = dest_info

    lf = "\r\n"
    boundary = "-----AaB03xeql7ds"
    hb = "--" + boundary
    pbegin = hb + lf
    psep = lf + pbegin
    pend = lf + hb + "--" + lf
    parts = []

    metaparthead = "Content-Disposition: form-data; name=\"metadata\"; filename=\"postcard-metadata.json\"\r\nContent-Type: application/json; charset=UTF-8\r\n"
    metapartbody = simplejson.dumps(filter_nan(card.metadata))
    metapart = lf.join([metaparthead, metapartbody])
    parts.append(metapart)

    if card.filedata is not None:
        filedatapartbody = card.filedata
        filedataparthead = "Content-Disposition: form-data; name=\"filedata\"; filename=%s\r\nContent-Type: application/octet-stream\r\nContent-Transfer-Encoding: binary\r\n" % filename_str_encode(card.filedataname)
        filedatapart = lf.join([filedataparthead, filedatapartbody])
        parts.append(filedatapart)

    if card.picfile is not None:
        #print repr(card.picfile)
        picpartbody = read_file(card.picfile)
        #print repr(picpartbody)
        picparthead = "Content-Disposition: form-data; name=\"picture\"; filename=%s\r\nContent-Type: image/jpeg\r\nContent-Transfer-Encoding: binary\r\n" % filename_str_encode(ut.basename(card.picfile))
        picpart = lf.join([picparthead, picpartbody])
        parts.append(picpart)

    uppartbody = "Upload"
    upparthead = "Content-Disposition: form-data; name=\"upload\"\r\n"
    uppart = lf.join([upparthead, uppartbody])
    parts.append(uppart)

    body = "".join([pbegin, psep.join(parts), pend])
    body_len = len(body)
    header = "POST %s HTTP/1.1\r\nHost: %s:%d\r\nConnection: close\r\nContent-type: multipart/form-data, boundary=%s\r\nContent-Length: %d\r\n" % (path, host, port, boundary, body_len)
    request = "".join([header, "\r\n", body])
    return request

class ReadExp:
    def __init__(self, max, sock, cb):
        self.max = max
        self.len = 0
        self.sock = sock
        self.data = ""
        self.cb = cb

    def read(self):
        amount = (ut.get_debug_on() and 1024 or (self.max - self.len))
        self.sock.read_some(amount, self._read, None)

    def _read(self, err, data, udata):
        ut.report((err, data, udata))
        if err != 0:
            self.cb(err, None)
        else:
            self.data += data
            self.len += len(data)
            if self.len == self.max:
                self.cb(err, self.data)
            elif self.len > self.max:
                self.cb(err, self.data[0:self.max])
            else:
                self.read()

http_accepted = "HTTP/1.1 200 "
http_refused = "HTTP/1.1 400 "

class Uploader:
    def __init__(self, config):
        self.config = config
        self.host, self.port, self.path = dest_info
        self.serv = None
        self.conn = None
        self.sock = None
        self.apid = None

    def send(self, card_data, cb):
        if self.sock:
            raise "still sending"

        self.cb = cb
        self.data = card_data
        apid = self.config.get_apid()

        if not self.serv:
            self.serv = AoSocketServ()
            self.serv.connect()

        if (apid is None) or (apid != self.apid):
            if self.conn:
                self.conn.close()
                self.conn = None
        self.apid = apid
        if (self.apid is not None) and (not self.conn):
            try:
                self.conn = AoConnection()
                self.conn.open(self.serv, self.apid)
            except:
                self.conn = None
                ut.print_exception()

        self.sock = AoSocket()
        try:
            self.sock.set_socket_serv(self.serv)
            if self.conn:
                self.sock.set_connection(self.conn)
            self.sock.open_tcp()
            #print "making connect request"
            self.sock.connect_tcp(unicode(self.host), self.port, self._connected, None)
            #print "now connecting"
        except:
            self.sock.close()
            self.sock = None

    def _connected(self, *args):
        #print repr(["_connected", args])
        err, udata = args
        if err:
            self.cancel()
            self.cb(err, None)
        else:
            self.sock.write_data(self.data, self._written, None)

    def _written(self, *args):
        #print repr(["_written", args])
        err, udata = args
        if err:
            self.cancel()
            self.cb(err, None)
        else:
            self.reader = ReadExp(len(http_accepted), self.sock, self._read)
            self.reader.read()

    def _read(self, serr, data):
        #print repr(["_read", serr, data])
        self.cancel()
        if not serr:
            if data == http_accepted:
                equ = "accepted"
            elif data == http_refused:
                equ = "refused"
            else:
                equ = "other"
        self.cb(serr, equ)

    def cancel(self):
        if self.sock:
            self.sock.close()
            self.sock = None

    def close(self):
        self.cancel()
        if self.conn:
            self.conn.close()
        if self.serv:
            self.serv.close()
        self.data = None # to save memory

class Card:
    """
    This object both stores and updates the card data, in some cases
    automatically, and in some cases upon request. Any persistent data
    is replicated in the Config instance, and initial values come from
    there if available.
    """
    
    def __init__(self, config, cb):
        self.config = config
        self.cb = cb
        self.clear()

    def clear(self):
        self.mood = self.config.db.get("mood", u"")
        self.sender = self.config.db.get("sender", {})
        self.recipient = self.config.db.get("recipient", private_recipient)
        self.picfile = self.config.db.get("picfile", None)
        if self.picfile and (not os.path.isfile(ut.to_str(self.picfile))):
            self.picfile = None
        self.clear_temporary()

    def clear_temporary(self):
        """
        Retains both sender and recipient.
        """
        self.filedataname = None
        self.filedata = None
        self.btprox = None
        self.gsm = None
        self.gps = None
        self.gps_gui = None

        if os.path.isfile(ut.to_str(test_filedata)):
            self.filedataname = ut.basename(test_filedata)
            self.filedata = read_file(test_filedata)
        
        self.update_timestamp("all")

    def clear_context(self):
        self.remove_gsm()
        self.remove_gps()
        self.remove_btprox()

    def set_gps(self, value):
        if value != self.gps:
            self.gps = value

            # To avoid needless GUI refreshing, we only signal when
            # the change is visible.
            if value is None:
                guival = None
            else:
                pos = value["position"]
                lat = pos["latitude"]
                lon = pos["longitude"]
                alt = pos["altitude"]
                guival = (lat, lon, alt)
            if self.gps_gui != guival:
                self.gps_gui = guival
                self.update_timestamp("gps")

    def remove_gps(self):
        self.set_gps(None)

    def view_gps(self, tech):
        if self.gps is None:
            appuifw.note(u"Position not acquired", "error")
            return
        pos = self.gps["position"]
        flist = [ (u"Latitude", "text", unirepr(pos["latitude"])),
                  (u"Longitude", "text", unirepr(pos["longitude"])),
                  (u"Altitude", "text", unirepr(pos["altitude"])),
                  (u"Vertical accuracy", "text", unirepr(pos["vertical_accuracy"])),
                  (u"Horizontal accuracy", "text", unirepr(pos["horizontal_accuracy"])) ]
        cou = self.gps["course"]
        if cou is not None:
            flist.extend([
                (u"Speed", "text", unirepr(cou["speed"])),
                (u"Heading", "text", unirepr(cou["heading"])),
                (u"Speed accuracy", "text", unirepr(cou["speed_accuracy"])),
                (u"Heading accuracy", "text", unirepr(cou["heading_accuracy"])),
                (u"Technology", "text", unicode(tech))
                ])
        form = appuifw.Form(flist, appuifw.FFormDoubleSpaced|
                            appuifw.FFormViewModeOnly)
        form.execute()
        #print repr(self.gps)

    def set_gsm(self, value):
        if value != self.gsm:
            self.gsm = value
            self.update_timestamp("gsm")

    def remove_gsm(self):
        self.set_gsm(None)

    def view_gsm(self):
        if self.gsm is None:
            appuifw.note(u"Network info not acquired", "error")
            return
        g = self.gsm
        flist = [ (u"Mobile Country Code", "number", g[0]),
                  (u"Mobile Network Code", "number", g[1]),
                  (u"Location Area Code", "number", g[2]),
                  (u"Cell ID", "number", g[3]) ]
        form = appuifw.Form(flist, appuifw.FFormDoubleSpaced|
                            appuifw.FFormViewModeOnly)
        form.execute()

    def view_btprox(self):
        if self.btprox is None:
            appuifw.note(u"Proximity not scanned for Bluetooth devices", "error")
            return
        if self.btprox == []:
            appuifw.note(u"No Bluetooth devices in proximity", "info")
            return
        # The Forms apparently do not like having more than 20 or so
        # items.
        flist = [ (unicode(d["mac"]), "text", unicode(d["name"])) for
                  d in self.btprox ][:20]
        form = appuifw.Form(flist, appuifw.FFormDoubleSpaced|
                            appuifw.FFormViewModeOnly)
        form.execute()

    def set_btprox(self, value):
        if value != self.btprox:
            self.btprox = value
            self.update_timestamp("btprox")

    def remove_btprox(self):
        self.set_btprox(None)

    def set_mood(self, text):
        if self.mood != text:
            self.mood = text
            self.config.db["mood"] = text
            self.config.save()
            self.update_timestamp("mood")

    def set_filedata(self, desc, data):
        self.filedataname = desc
        self.filedata = data
        self.update_timestamp("filedata")

    def remove_filedata(self):
        if self.filedata:
            self.filedata = None
            self.update_timestamp("filedata")

    def set_picfile(self, new_picfile):
        old_picfile = self.picfile
        if new_picfile != old_picfile:
            self.picfile = new_picfile
            self.config.db["picfile"] = new_picfile
            self.config.save()
            self.update_timestamp("picfile")

    def remove_picfile(self):
        self.set_picfile(None)

    def set_sender(self, new_sender):
        old_sender = self.sender
        if new_sender != old_sender:
            self.sender = new_sender
            self.config.db["sender"] = new_sender
            self.config.save()
            self.update_timestamp("sender")

    def set_recipient(self, new_recipient):
        old_recipient = self.recipient
        if new_recipient != old_recipient:
            self.recipient = new_recipient
            self.config.db["recipient"] = new_recipient
            self.config.save()
            self.update_timestamp("recipient")

    def update_timestamp(self, field):
        tm = time.time()
        tmrec = {"time" : tm,
                 "timezone" : time.timezone,
                 "daylight" : time.daylight and True or False}
        if time.daylight:
            tmrec["altzone"] = time.altzone
        self.time = tmrec

        if self.cb:
            self.cb(field)

    def refresh_metadata(self):
        metadata = self.metadata = {}
        if self.filedata:
            metadata["data filename"] = self.filedataname
        if self.picfile:
            metadata["photo filename"] = ut.basename(self.picfile)
        metadata["sender"] = self.sender
        metadata["receiver"] = self.recipient
        metadata["status"] = self.mood
        
        if self.gps is not None:
            metadata["gps"] = self.gps
        
        if self.btprox:
            metadata["bt scan"] = self.btprox

        if self.gsm is not None:
            (country_code, network_code, area_code, cell_id) = self.gsm
            metadata["gsm"] = {"country code" : country_code, "network code" : network_code, "area code" : area_code, "cell id" : cell_id}
        
        metadata["time"] = self.time

    def has_any_sender(self):
        return self.sender != {}

    def has_valid_sender(self):
        return self.sender.has_key("email_address")

    def has_any_recipient(self):
        return self.recipient != {}

    def has_valid_recipient(self):
        return self.recipient.has_key("email_address")

    def validate(self):
        """
        Validates that any and all data required in the card before it
        can be sent is there. Returns True or False, and shows an
        error dialog as appropriate.
        """
        if not (self.sender.has_key("email_address")):
            appuifw.note(u"No sender email address", "error")
        elif not (self.recipient.has_key("email_address")):
            appuifw.note(u"No recipient email address", "error")
        else:
            return True
        return False

    def prepare_for_sending(self):
        self.refresh_metadata()

max_read = 1024

# xxx We could do with less memory by reading data in chunks and
# uploading the chunks as we go.
def inbox_read_data(inbox, msg_id):
    datalen = inbox.size(msg_id)
    read = 0
    data = []
    while read < datalen:
        thismax = datalen - read
        if thismax > max_read:
            thismax = max_read
        s = inbox.data(msg_id, read, thismax)
        read += len(s)
        data.append(s)
    return "".join(data)

KUidMsgTypeBt = 0x10009ED5

class FiledataReader:
    """
    Observes Inbox, and handles the reading of filedata.
    """
    def __init__(self, cb):
        """
        cb:: Called with description and data when new filedata is
             available.
        """
        self.inbox = None
        self.timer = e32.Ao_timer()
        self.cb = cb

    def start_observing(self):
        if self.inbox is None:
            self.inbox = pyinbox.Inbox(KUidMsgTypeBt)
            self.inbox.bind(self.message_arrived)
            ut.report("observing Inbox")

    def stop_observing(self):
        if self.inbox is not None:
            self.inbox = None
            ut.report("not observing Inbox")

    def is_observing(self):
        return self.inbox is not None

    def message_arrived(self, id):
        # At the time we get a message arrival event, it is not yet in
        # Inbox, and many of the Inbox methods fail to work on that
        # message. So we just record the ID, and handle it after the
        # callback has returned.
        if self.inbox:
            ut.report("got message %d" % id)

            if self.is_bt_message(id):
                # xxx yes, there is a period of time where a message could be lost
                self.later_do(lambda: self._examine(id))
            else:
                ut.report("ignoring non-BT message")

    def is_bt_message(self, id):
        return (self.inbox.message_type(id) == KUidMsgTypeBt)

    def later_do(self, cb):
        self.timer.cancel()
        # xxx the message is typically not in the Inbox immediately after the message event callback returns -- we just wait some random amount of time for now, and hope for the best -- N95 is fine with 3 secs, but E71 seems slower -- also on E71 the scanning (GPS or something seems to interfere with sending to inbox)
        self.timer.after(5, cb)

    def _examine(self, id):
        ut.report("examining message %d" % id)
        try:
            ut.report("message size is %d" % self.inbox.size(id))
            desc = self.inbox.description(id)
            if self.is_filedata_message(id, desc):
                data = inbox_read_data(self.inbox, id)
                ut.report("message fetched")
                self.inbox.delete(id)
                ut.report("message deleted")
                self.cb(desc, data)
            else:
                ut.report("ignoring non-Filedata message")
        except:
            ut.report("failed to handle message")
            ut.print_exception()

    def is_filedata_message(self, id, desc):
        # We can check for any filename pattern here.
        # Reading the contents would require more work.
        return (desc[-4:] == ".doc")

    def close(self):
        self.stop_observing()
        self.timer.cancel()

if os.path.exists("e:\\data"):
    uploads_dir = "e:\\data\\tpytwink\\uploads\\"
else:
    uploads_dir = "c:\\data\\tpytwink\\uploads\\"

def save_unsent_card(data):
    tm = time.time()
    tm_s = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime(tm))
    filename = uploads_dir + tm_s + ".txt"
    make_file(filename, data)

class ScannerSender:
    """
    The task of an object of this type is to add context data and send
    it, reporting on success or failure with a callback.
    """
    def __init__(self, config):
        """
        apid: Initial access point ID to use.
        """
        self.config = config
        self.gsm_scanner = GsmScanner()
        self.btprox_scanner = None
        self.positioner = None
        self.uploader = Uploader(config)
        self.immediate = AoImmediate()
        self.immediate.open()
        self.btprox_scan_error_shown = False
        self.active = False

    def cancel(self):
        """
        Cancels any operation(s) in progress, whether finished or not.
        """
        self.immediate.cancel()
        self.gsm_scanner.cancel()
        if self.btprox_scanner:
            self.btprox_scanner.cancel()
        if self.positioner:
            self.positioner.cancel()
        self.uploader.cancel()
        self.active = False

    def close(self):
        """
        Does cleanup.
        """
        self.immediate.close()
        self.gsm_scanner.close()
        if self.btprox_scanner:
            self.btprox_scanner.close()
        if self.positioner:
            self.positioner.close()
        self.uploader.close()

    def scan_and_send(self, card, cb):
        """
        The caller of this method should check the "active" flag to
        ensure that no send is already in progress.
        
        card:: Card to which to add context data and to send.
        cb:: Status reporting callback.
        """
        if self.active: raise "assertion failure"

        self.card = card
        self.cb = cb

        self._clear_context()
        if self.config.get_noscan():
            self._send_card()
        else:
            self._scan_gsm()

    def _clear_context(self):
        """
        Note that it is important to set values to None when scanning
        fails so that we never end up sending a card with an old
        value.
        """
        self.card.set_gsm(None)
        self.card.set_btprox(None)

    def _scan_gsm(self):
        ut.report("_scan_gsm")
        def f():
            self.gsm_scanner.scan(self._gsm_done)
            self.active = True
        self.cb("progress", u"Scanning context")
        self._via_immediate(f)

    def _gsm_done(self, gsm):
        """
        Note that it is important to set values to None when scanning
        fails so that we never end up sending a card with an old
        value.
        """
        ut.report("_gsm_done")
        self.active = False
        self.card.set_gsm(gsm)
        self._scan_btprox()

    def init_btprox_scanner(self):
        try:
            self.btprox_scanner = BtproxScanner()
        except:
            self.btprox_scanner = None

    def _scan_btprox(self):
        ut.report("_scan_btprox")
        try:
            if not self.config.get_btprox_scan():
                self._btprox_done(None)
                return
            if not self.btprox_scanner:
                self.init_btprox_scanner()
            if not self.btprox_scanner:
                if not self.btprox_scan_error_shown:
                    self.btprox_scan_error_shown = True
                    appuifw.note(u"Could not scan proximity: Is Bluetooth enabled?", "error")
                self._btprox_done(None)
                return
            self.btprox_scanner.scan(self._btprox_done)
            self.active = True
        except:
            ut.print_exception()
            self._btprox_done(None)

    def _btprox_done(self, btdata):
        """
        btdata:: Has value None if there was a scanning error.
        """
        ut.report("_btprox_done")
        self.active = False
        if btdata is None:
            self.btprox_scanner = None
        self.card.set_btprox(btdata)
        if self.card.gps is None:
            # Our positioning hack no longer appears to work, so disabling for now.
            #self._scan_position()
            self._send_card()
        else:
            self._send_card()

    def _scan_position(self):
        ut.report("_scan_position")

        def f():
            if self.positioner:
                self.positioner.close()
                self.positioner = None
            try:
                from pytwink import Positioner

                modlist = positioning.modules()
                module_id = None
                for entry in modlist:
                    if entry["name"] == u"Network based" and \
                       entry["available"]:
                        module_id = entry["id"]
                        break
                if not module_id:
                    raise "no network positioning module"

                updatetimeout = 15000000
                maxupdateage =  30000000
                self.positioner = Positioner(module_id, updatetimeout, maxupdateage)
                self.positioner.ask_position(self._positioner_done)
                return
            except:
                self._send_card()

            self.active = True

        self.cb("progress", u"Querying position")
        self._via_immediate(f)

    def _positioner_done(self, code):
        ut.report("_positioner_done (%d)" % code)
        self.active = False
        if not code:
            self.card.gps = {"position": self.positioner.get_position()}
        self._send_card()

    def _send_card(self):
        if self.config.get_store_on():
            self.cb("progress", u"Storing card")
            def f():
                try:
                    self.card.prepare_for_sending()
                    data = serialize_card(self.card)
                    save_unsent_card(data)
                    self.cb("ok", u"Card stored")
                except:
                    ut.print_exception()
                    self.cb("fail", u"Storing failed")
        else:
            self.cb("progress", u"Sending card")
            def f():
                try:
                    self.card.prepare_for_sending()
                    self.uploader.send(serialize_card(self.card), self._send_done)
                    self.active = True
                except:
                    self.config.set_apid(None)
                    ut.print_exception()
                    #appuifw.note(u"Sending failed", "error")
                    self.cb("fail", u"Sending failed")
        self._via_immediate(f)

    def _send_done(self, serr, equ):
        self.active = False
        if serr:
            ut.report("send error (Symbian %d)" % serr)
            self.cb("fail", u"Sending failed")
        elif equ == "refused":
            self.cb("fail", u"Server did not accept card")
        elif equ == "accepted":
            self.cb("ok", u"Card sent")
        else:
            self.cb("fail", u"Unexpected response from server")

    def _via_immediate(self, cb):
        def this_cb(code, dummy):
            self.active = False
            cb()
        self.immediate.complete(this_cb, None)
        self.active = True

tpytwink_logdir = u'c:\\logs\\tpytwink\\'
configdb_file = u'c:\\data\\tpytwink\\settings.txt'

class Config:
    """
    It is useful for us to have the configuration in a dedicated
    object, to allow other objects to access the configuration and
    even modify it.
    """
    def __init__(self):
        # This maintains the master copy of our settings. These
        # settings are copied to the model(s) as required, but any
        # changes happen first in this model.
        self.db = {}

        self.load()

    def load(self):
        """
        Loads the configuration. Anything not in the configuration
        file will get its default value.
        """
        try:
            fp = open(configdb_file, "r")
            try:
                data = fp.read()
            finally:
                fp.close()
        except IOError:
            # If say the file does not yet exist.
            return

        try:
            elocals = {}
            exec(data, {}, elocals)
            #print repr(elocals)
            self.db = elocals["data"]
        except:
            pass

    def save(self):
        fp = open(configdb_file, "w")
        try:
            fp.write("data = " + repr(self.db))
        finally:
            fp.close()

    # ------------------------------------------------------------------
    # apid...

    def get_apid(self):
        # The default value is None, as in no access point selected.
        return self.db.get("apid", None)

    def set_apid(self, apid):
        if self.get_apid() == apid:
            return
        self.db["apid"] = apid
        self.save()
        
    def change_apid(self):
        apid = None
        try:
            # Will return None if the user selects nothing, and that
            # is fine. Or it would be, if this call did not produce a
            # KERN-EXEC 3 almost every time.
            #apid = socket.select_access_point()

            apid = my_select_access_point()
        except:
            appuifw.note(u"Failed to select", "error")
            ut.print_exception()

        self.set_apid(apid)

    # ------------------------------------------------------------------
    # noscan...

    def get_noscan(self):
        """
        The only semantics of the "noscan" flag is to indicate whether
        context scanning may be started, and whether scanning may be
        done just prior to a send. This flag is provided for debugging
        purposes only.
        """
        return self.db.get("scanning_forbidden", False)

    def set_noscan(self, on):
        """
        Sets (and saves) specified scanning configuration.
        """
        if self.get_noscan() == on:
            return
        self.db["scanning_forbidden"] = on
        self.save()
        appuifw.note(u"Scanning forbidden: %s" % (on and "true" or "false"), "info")
        
    def toggle_noscan(self):
        self.set_noscan(not self.get_noscan())

    # ------------------------------------------------------------------
    # btprox_scan...

    def get_btprox_scan(self):
        """
        The only semantics of the "btprox_scan" flag is to indicate
        whether btprox scanning may be done just prior to a send.
        """
        return self.db.get("btprox_scanning_enabled", True)

    def set_btprox_scan(self, on):
        """
        Sets (and saves) specified scanning configuration.
        """
        if self.get_btprox_scan() == on:
            return
        self.db["btprox_scanning_enabled"] = on
        self.save()
        appuifw.note(u"BT scanning %s" % (on and "enabled" or "disabled"), "info")
        
    def toggle_btprox_scan(self):
        self.set_btprox_scan(not self.get_btprox_scan())

    # ------------------------------------------------------------------
    # gps_scan...

    def get_gps_scan(self):
        """
        The only semantics of the "gps_scan" flag is to indicate
        whether GPS scanning may run on the background.
        """
        return self.db.get("gps_scanning_enabled", True)

    def set_gps_scan(self, on):
        """
        Sets (and saves) specified scanning configuration.
        """
        if self.get_gps_scan() == on:
            return
        self.db["gps_scanning_enabled"] = on
        self.save()
        appuifw.note(u"GPS scanning %s" % (on and "enabled" or "disabled"), "info")
        
    def toggle_gps_scan(self):
        self.set_gps_scan(not self.get_gps_scan())

    # ------------------------------------------------------------------
    # store or send...

    def get_store_on(self):
        """
        The only semantics of the "store_on" flag is to indicate
        whether to store in a file rather than try sending.
        """
        return self.db.get("store_on", False)

    def set_store_on(self, on):
        if self.get_store_on() == on:
            return
        self.db["store_on"] = on
        self.save()
        appuifw.note(u"Storing %s" % (on and "enabled" or "disabled"), "info")
        
    def toggle_store_on(self):
        self.set_store_on(not self.get_store_on())

class Engine:
    """
    This engine object maintains the model of the application. The
    engine itself fills in and maintains the context information in
    the model, and does this quietly on the background for the
    lifetime of the engine. Filedata scanning can be toggled on and
    off by the controller. Some data is user-editable, and the engine
    provides utilities for querying that data from the user. The
    engine also implements some actions such as message sending, and
    this functionality is available upon request by the controller.
    """
    def __init__(self):
        self.config = Config()
        self.apply_debug_config()

        self.scanner_sender = ScannerSender(self.config)
        self.card = Card(self.config, lambda field: None)
        self._init_gps_scanner()
        self.reader = FiledataReader(self._new_filedata)

        self._configdb_loaded()

        self.context_start_scanning()
        
    def is_ready_to_send(self):
        if not self.card.validate():
            return False
        if self.scanner_sender.active:
            appuifw.note(u"Still sending", "error")
            return False
        return True

    def send_card(self, cb):
        """
        cb:: A callable taking two arguments, e.g. "ok" and u"Card sent".
        Returns:: A true value if a callback is to be expected.
        """
        self.scanner_sender.scan_and_send(self.card, cb)

    def context_start_scanning(self):
        """
        Starts any constant context scanning that is enabled.
        
        It is safe to call this even when already scanning.
        """
        if self.config.get_noscan():
            return
        if self.config.get_gps_scan():
            self._gps_start_scanning()
        ut.report("context scanning started")
        
    def context_stop_scanning(self):
        """
        Stops all constant context scanning.
        """
        self._gps_stop_scanning()
        ut.report("context scanning stopped")

    def _init_gps_scanner(self):
        """
        It is valid for "self.gps_scanner" to be None, since the
        capabilities required to access GPS may not be available. If
        this method fails, then "self.gps_scanner" will be set to
        None, and will stay that way. To change the used positioning
        module, invoke the appropriate methods on the scanner.
        """
        self.gps_scanner = None
        if gps_avail:
            try:
                omid = self.config.db.get("gps_module_id", None)
                self.gps_scanner = GpsScanner(self._gps_scanned, omid)
            except:
                if ut.get_debug_on():
                    ut.print_exception()
                    ut.report("GPS scanner init failure")
                self.gps_scanner = None
        else:
            ut.report("GPS not available")

    def get_gps_scan(self):
        return self.config.get_gps_scan()

    def set_gps_scan(self, on):
        is_on = self.get_gps_scan()
        if on == is_on: return
        self.config.set_gps_scan(on)
        if on:
            self._gps_start_scanning()
        else:
            self._gps_stop_scanning()

    def toggle_gps_scan(self):
        self.set_gps_scan(not self.get_gps_scan())

    def _gps_start_scanning(self):
        if self.gps_scanner is not None:
            self.gps_scanner.start()

    def _gps_stop_scanning(self):
        if self.gps_scanner is not None:
            self.gps_scanner.stop()
        self.card.set_gps(None)

    def _gps_scanned(self, data):
        #print repr(data)
        self.card.set_gps(data)

    def edit_gps_config(self):
        if not self.gps_scanner:
            appuifw.note(u"GPS not supported", "error")
            return

        nmid = self.gps_scanner.choose_module()
        if nmid is None:
            return

        omid = self.config.db.get("gps_module_id", None)
        if omid != nmid:
            self.config.db["gps_module_id"] = nmid
            self.config.save()
            self.gps_scanner.use_module(nmid)

    def show_gps(self):
        if self.gps_scanner:
            if self.card.gps:
                self.card.view_gps(self.gps_scanner.module_gui_name())
            elif self.gps_scanner.active:
                appuifw.note(u"No GPS data yet, but scanning with %s" % self.gps_scanner.module_gui_name(), "info")
            else:
                appuifw.note(u"GPS not currently being scanned")
        else:
            appuifw.note(u"GPS not supported", "error")

    def show_btprox(self):
        if self.card.btprox is not None:
            self.card.view_btprox()
        elif self.btprox_scanner is None:
            appuifw.note(u"Bluetooth proximity scans unsuccessful", "error")
        elif self.btprox_scanner.scanning:
            appuifw.note(u"No Bluetooth proximity data yet, but scan in progress", "info")
        else:
            appuifw.note(u"No Bluetooth proximity data yet", "info")

    def show_gsm(self):
        self.card.view_gsm()

    def _new_filedata(self, desc, data):
        appuifw.note(u"New data file acquired", "info")
        self.card.set_filedata(desc, data)
        self.filedata_cb()

    _setting_map = [
        ("title", u"Title"),
        ("first_name", u"First name"),
        ("second_name", u"Second name"),
        ("last_name", u"Last name"),
        ("email_address", u"Email address"),
        ("first_name_reading", u"First name reading"),
        ("last_name_reading", u"Last name reading")
        ]

    def _name_to_gui(self, name):
        for n,g in self._setting_map:
            if name == n:
                return g
        raise "assertion failure"

    def _gui_to_name(self, s):
        for n,g in self._setting_map:
            if g == s:
                return n
        raise "assertion failure"

    def _edit_contact(self, old_value):
        def fv(name):
            return (self._name_to_gui(name),
                    "text",
                    old_value.get(name, u""))

        form = appuifw.Form(
            [
            fv("title"),
            fv("first_name"),
            fv("second_name"),
            fv("last_name"),
            fv("email_address"),
            fv("first_name_reading"),
            fv("last_name_reading")
            ],
            appuifw.FFormEditModeOnly|
            appuifw.FFormDoubleSpaced)
        form.execute() # always returns None apparently

        new_value = {}
        for n,t,v in form:
            if v != "":
                new_value[self._gui_to_name(n)] = v

        if new_value == old_value:
            return None
        return new_value

    def _configdb_loaded(self):
        """
        Propagates any settings in "self.config.db" to the relevant
        models and views.
        """
        self.apply_debug_config()
        self.card.set_sender(self.config.db.get("sender", {}))

    def apply_debug_config(self):
        """
        Applies current debug configuration.
        """
        debug_on = self.config.db.get("debug", False)
        ut.set_debug_on(debug_on)

    def toggle_debug_on(self):
        self.set_debug_on(not self.get_debug_on())

    def get_debug_on(self):
        return ut.get_debug_on()

    def set_debug_on(self, on):
        """
        Sets (and saves) specified debug configuration.
        """
        debug_on = self.get_debug_on()
        if debug_on == on:
            return
        self.config.db["debug"] = debug_on = on
        ut.set_debug_on(debug_on)
        self.config.save()
        appuifw.note(u"Debugging %s" % (debug_on and "on" or "off"), "info")

    def remove_sender(self):
        self.card.set_sender({})

    def edit_sender(self):
        new_sender = self._edit_contact(self.card.sender)
        if new_sender is not None:
            self.card.set_sender(new_sender)

    def select_sender(self):
        new_sender = select_contact(False)
        if new_sender is not None:
            self.card.set_sender(new_sender)

    def set_public_recipient(self):
        self.card.set_recipient(public_recipient)

    def set_private_recipient(self):
        self.card.set_recipient(private_recipient)
    
    def select_recipient(self):
        new_value = select_contact(True)
        if new_value is not None:
            self.card.set_recipient(new_value)

    def edit_recipient(self):
        new_value = self._edit_contact(self.card.recipient)
        if new_value is not None:
            self.card.set_recipient(new_value)

    def remove_recipient(self):
        self.card.set_recipient({})

    def show_log_file(self):
        ut.show_log(tpytwink_logdir)

    def select_camera_uid(self):
        old_uid = self.config.db.get("camera_uid", 0x101ffa86)
        nums = [0x101ffa86, 0x101f857a]
        chlist = [ (u"0x%08X" % uid) for uid in nums ]
        index = appuifw.popup_menu(chlist, u'Select Camera UID')
        if index is not None:
            new_uid = nums[index]
            if old_uid != new_uid:
                self.config.db["camera_uid"] = new_uid
                self.config.save()

    def take_photo(self):
        newfile = None
        uid = self.config.db.get("camera_uid", 0x101ffa86)
        try:
            newfile = pynewfile.take_photo(uid)
        except:
            if ut.get_debug_on():
                ut.print_exception()
            appuifw.note(u"Failed to take a photo", "error")
        if newfile is not None:
            self.card.set_picfile(newfile)

    def show_picfile(self):
        if self.card.picfile is not None:
            ut.show_doc(self.card.picfile)

    # xxx this function is problematic since it invalidates any already scanned gallery file listing
    def rename_picfile(self):
        if self.card.picfile is not None:
            dirname = ut.dirname(self.card.picfile)
            old_basename = ut.basename(self.card.picfile)
            new_basename = appuifw.query(u"Filename:", "text", old_basename)
            if new_basename is not None:
                new_picfile = dirname + "\\" + new_basename
                # Better check since on some platforms the target is
                # silently clobbered.
                if os.path.exists(ut.to_str(new_picfile)):
                    appuifw.note(u"File by that name already exists", "error")
                    return
                try:
                    os.rename(ut.to_str(self.card.picfile),
                              ut.to_str(new_picfile))
                except:
                    appuifw.note(u"Failed to rename photo", "error")
                    return
                self.card.set_picfile(new_picfile)

    def start_observing_filedata(self, cb):
        self.filedata_cb = cb
        self.reader.start_observing()

    def stop_observing_filedata(self):
        self.reader.stop_observing()

    def is_observing_filedata(self):
        return self.reader.is_observing()

    def close(self):
        if self.gps_scanner:
            self.gps_scanner.close()
        self.scanner_sender.close()
        self.reader.close()
