#
# default.py
#
# Copyright 2007 Helsinki Institute for Information Technology
# and the authors.
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
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# We want to launch a specific app always. This allows us to install a
# .py file in the usual location (from where the "Python" application
# looks for scripts to run), and also have that script launchable via
# its own icon. And the "application" only has to be installed once.
# 
# We want minimal functionality here, to leave it to the application
# to decide what to do in various situations. Particularly startup
# performance tends to be a problem for VM based languages, and we do
# not want to take time here doing things we do not know if the
# application requires.

import e32
import os
import sys
import appuifw

if (e32.s60_version_info >= (3,0)):
    for path in ('c:\\python\\lib', 'e:\\python\\lib'):
        if os.path.exists(path):
            sys.path.append(path)

app_path = os.path.split(appuifw.app.full_name())[0]
app_drive = app_path[:2]
app_script = app_drive + "\\python\\tpytwink_main.py"
app_script_c = app_drive + "\\python\\lib\\tpytwink_main.pyc"

if os.path.exists(app_script_c):
    import tpytwink_main
    tpytwink_main.main()
elif os.path.exists(app_script):
    execfile(app_script, globals())
