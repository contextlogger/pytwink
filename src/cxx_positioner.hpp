#ifndef __cxx_positioner_hpp__
#define __cxx_positioner_hpp__

#include <Python.h>
#include <e32std.h>

#include <lbs.h> // link against lbs.lib
#include <lbssatellite.h>

#include "common/epoc-session.hpp"

NONSHARABLE_CLASS(CCxxPositioner) :
  public CActive
{
 public:

  static CCxxPositioner* NewL(TPositionModuleId aModuleId,
			      TInt aUpdateTimeOut, // in microseconds
			      TInt aMaxUpdateAge // in microseconds
			      );

  virtual ~CCxxPositioner();

  void AskPosition(PyObject* aCallback);

  const TPosition& Position() const { return iPosition; }

 private:
 
  CCxxPositioner(TPositionModuleId aModuleId,
		 TInt aUpdateTimeOut, // in microseconds
		 TInt aMaxUpdateAge // in microseconds
		 );

  void ConstructL();

  void FreeCallback() { if (iCallback) { Py_DECREF(iCallback); iCallback = NULL; } }

  void PythonCall(TInt errCode);

 private: // CActive

  virtual void RunL();
  
  virtual TInt RunError(TInt aError);

  virtual void DoCancel();

 private:

  TPositionModuleId iModuleId;
  TInt iUpdateTimeOut; // in microseconds
  TInt iMaxUpdateAge; // in microseconds

  DEF_SESSION(RPositionServer, iPositionServer);
  DEF_SESSION(RPositioner, iPositioner);

  TPositionUpdateOptions iUpdateOptions;
  TPositionInfo iPositionInfo;
  TPosition iPosition;

  PyObject* iCallback;

};

#endif /* __cxx_positioner_hpp__ */

/**

Copyright 2010 Helsinki Institute for Information Technology (HIIT)
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
