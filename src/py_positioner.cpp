//
// Copyright 2009 Helsinki Institute for Information Technology (HIIT)
// and the authors.  All rights reserved.
//
// Authors: Tero Hasu <tero.hasu@hut.fi>
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

#include "py_positioner.hpp"
#include "cxx_positioner.hpp"

#include "application_config.h"
#include "common/panic.h"
#include "panic_list.hpp"

#include <symbian_python_ext_util.h>
#include "local_epoc_py_utils.h"

typedef struct
{
  PyObject_VAR_HEAD;
  CCxxPositioner* iCppObject;
} obj_Positioner;

static PyObject* meth_ask_position(obj_Positioner* self, PyObject* args)
{
  if (!self->iCppObject)
    Panic(EPanicSessionAlreadyClosed);

  PyObject* cb;
  if (!PyArg_ParseTuple(args, "O", &cb))
    {
      return NULL;
    }
  if (!PyCallable_Check(cb))
    {
      PyErr_SetString(PyExc_TypeError, "parameter must be callable");
      return NULL;
    }

  self->iCppObject->AskPosition(cb);
  
  RETURN_NO_VALUE;
}

static PyObject* meth_get_position(obj_Positioner* self, PyObject* /*args*/)
{
  if (!self->iCppObject)
    Panic(EPanicSessionAlreadyClosed);

  const TPosition& position = self->iCppObject->Position();

  // from pys60 source code (see "gps" directory)
  return Py_BuildValue("{s:d,s:d,s:d,s:d,s:d}",
		       "latitude", position.Latitude(),
		       "longitude", position.Longitude(),
		       "altitude", position.Altitude(),
		       "vertical_accuracy", position.VerticalAccuracy(),
		       "horizontal_accuracy", position.HorizontalAccuracy());
}

static PyObject* meth_cancel(obj_Positioner* self, PyObject* /*args*/)
{
  if (!self->iCppObject)
    Panic(EPanicSessionAlreadyClosed);
  self->iCppObject->Cancel();
  RETURN_NO_VALUE;
}

static PyObject* meth_close(obj_Positioner* self, PyObject* /*args*/)
{
  delete self->iCppObject;
  self->iCppObject = NULL;
  RETURN_NO_VALUE;
}

static const PyMethodDef Positioner_methods[] =
  {
    {"ask_position", (PyCFunction)meth_ask_position, METH_VARARGS, NULL},
    {"get_position", (PyCFunction)meth_get_position, METH_NOARGS, NULL},
    {"cancel", (PyCFunction)meth_cancel, METH_NOARGS, NULL},
    {"close", (PyCFunction)meth_close, METH_NOARGS, NULL},
    {NULL, NULL} /* sentinel */
  };

static void del_Positioner(obj_Positioner *self)
{
  delete self->iCppObject;
  self->iCppObject = NULL;
  PyObject_Del(self);
}

static PyObject *getattr_Positioner(obj_Positioner *self, char *name)
{
  return Py_FindMethod(METHOD_TABLE(Positioner), reinterpret_cast<PyObject*>(self), name);
}

const static PyTypeObject tmpl_Positioner =
  {
    PyObject_HEAD_INIT(NULL)
    0, /*ob_size*/
    "pytwink.Positioner", /*tp_name*/
    sizeof(obj_Positioner), /*tp_basicsize*/
    0, /*tp_itemsize*/
    /* methods */
    (destructor)del_Positioner, /*tp_dealloc*/
    0, /*tp_print*/
    (getattrfunc)getattr_Positioner, /*tp_getattr*/
    0, /*tp_setattr*/
    0, /*tp_compare*/
    0, /*tp_repr*/
    0, /*tp_as_number*/
    0, /*tp_as_sequence*/
    0, /*tp_as_mapping*/
    0 /*tp_hash*/
  };

TInt def_Positioner()
{
  return ConstructType(&tmpl_Positioner, "pytwink.Positioner");
}

PyObject* new_Positioner(PyObject* /*self*/, PyObject* args)
{
  TInt moduleIdInt, updateTimeOut, maxUpdateAge;
  if (!PyArg_ParseTuple(args, "iii", &moduleIdInt, &updateTimeOut, &maxUpdateAge))
  {
    return NULL;
  }
  TPositionModuleId moduleId;
  moduleId.iUid = moduleIdInt;

  PyTypeObject* typeObject = reinterpret_cast<PyTypeObject*>(SPyGetGlobalString("pytwink.Positioner"));
  obj_Positioner* self = PyObject_New(obj_Positioner, typeObject);
  if (self == NULL)
      return NULL;
  self->iCppObject = NULL;

  TRAPD(error,
	self->iCppObject = CCxxPositioner::NewL(moduleId, updateTimeOut, maxUpdateAge);
	);
  if (error) {
    PyObject_Del(self);
    return SPyErr_SetFromSymbianOSErr(error);
  }

  return reinterpret_cast<PyObject*>(self);
}
