#include "py_get_position.hpp"
#include "cxx_get_position.hpp"
#include <symbian_python_ext_util.h>
#include "local_epoc_py_utils.h"
#include <lbscommon.h>

PyObject *py_GetCurrentPosition(PyObject *, PyObject *args)
{
  TInt moduleIdInt;
  if (!PyArg_ParseTuple(args, "i", &moduleIdInt))
  {
    return 0;
  }
  TPositionModuleId moduleId;
  moduleId.iUid = moduleIdInt;

  TPosition position;
  TRAPD(errCode,
	GetCurrentPositionL(position, moduleId);
        );
  if (errCode) {
    return SPyErr_SetFromSymbianOSErr(errCode);
  }

  // from pys60 source code (see "gps" directory)
  return Py_BuildValue("{s:d,s:d,s:d,s:d,s:d}",
		       "latitude", position.Latitude(),
		       "longitude", position.Longitude(),
		       "altitude", position.Altitude(),
		       "vertical_accuracy", position.VerticalAccuracy(),
		       "horizontal_accuracy", position.HorizontalAccuracy());
}

/**

Copyright 2009 Helsinki Institute for Information Technology (HIIT)
and the authors. All rights reserved.

Authors: Tero Hasu <tero.hasu@hut.fi>

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation files
(the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge,
publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

 **/
