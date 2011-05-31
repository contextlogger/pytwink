import e32
import positioning

modlist = positioning.modules()
print(repr(modlist))

module_id = None
for entry in modlist:
    if entry["name"] == u"Network based" and \
       entry["available"]:
        module_id = entry["id"]
        break

if not module_id:
    print "no suitable module"
else:
    from pytwink import Positioner

    updatetimeout = 15000000
    maxupdateage =  30000000
    positioner = Positioner(module_id, updatetimeout, maxupdateage)

    myLock = e32.Ao_lock()

    def cb(errCode):
        print repr(errCode)
        if not errCode:
            print repr(positioner.get_position())
        myLock.signal()

    try:
        print "asking position"
        positioner.ask_position(cb)
        positioner.cancel()
        positioner.ask_position(cb)
        myLock.wait()
    finally:
        positioner.close()

print "all done"
