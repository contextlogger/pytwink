//
// Copyright 2008 Helsinki Institute for Information Technology (HIIT)
// and the authors. All rights reserved.
//
// Authors: Tero Hasu <tero.hasu@hut.fi>
//

// Except where otherwise noted, this license applies:
//
// Permission is hereby granted, free of charge, to any person
// obtaining a copy of this software and associated documentation files
// (the "Software"), to deal in the Software without restriction,
// including without limitation the rights to use, copy, modify, merge,
// publish, distribute, sublicense, and/or sell copies of the Software,
// and to permit persons to whom the Software is furnished to do so,
// subject to the following conditions:
//
// The above copyright notice and this permission notice shall be
// included in all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
// EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
// MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
// NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
// BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
// ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
// CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

#include <e32std.h>
#include <eikbtgpc.h>

#include <Python.h>
#include <symbian_python_ext_util.h>
#include "local_epoc_py_utils.h"

#include "py_get_position.hpp"
#include "py_positioner.hpp"

// -------------------------------------------------------
// Python module...

// This code comes from http://code.google.com/p/uikludges/, and is
// used under the New BSD License.
static PyObject *_fn__pytwink__set_softkey_text(PyObject *, PyObject *args)
{
  char* text_ = 0;      
  TInt key;
  TInt textlen = 0;  
  if (!PyArg_ParseTuple(args, "iu#", &key, &text_, &textlen))
  {
    return 0;
  }
  TPtrC text((TUint16*)text_, textlen);

  TRAPD(err,
        CEikButtonGroupContainer::Current()->SetCommandL(key, text);
        CEikButtonGroupContainer::Current()->DrawDeferred();
        );
  
  RETURN_ERROR_OR_PYNONE(err);
}

static PyMethodDef const _ft__pytwink[] = {
  {"set_softkey_text", reinterpret_cast<PyCFunction>(_fn__pytwink__set_softkey_text), METH_VARARGS, NULL},
  {"get_current_position", reinterpret_cast<PyCFunction>(py_GetCurrentPosition), METH_VARARGS, NULL},
  {"Positioner", (PyCFunction)new_Positioner, METH_VARARGS},
  {NULL}};

EXPORT_C void initpytwink()
{
  PyObject *pyMod = Py_InitModule("pytwink", const_cast<PyMethodDef *>((&_ft__pytwink[0])));
  if ((pyMod == NULL)) {
    return;
  }
  if (def_Positioner() < 0) return;
}

#ifndef EKA2
GLDEF_C TInt E32Dll(TDllReason)
{
  return KErrNone;
}
#endif
