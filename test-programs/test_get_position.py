from pytwink import *
import positioning

modlist = positioning.modules()
print(repr(modlist))

for entry in modlist:
    if entry["name"] == u"Network based" and \
       entry["available"]:
        module_id = entry["id"]
        print(repr(get_current_position(module_id)))
