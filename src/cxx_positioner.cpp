#include "cxx_positioner.hpp"

#include "application_config.h"
#include "common/panic.h"
#include "panic_list.hpp"

// -------------------------------------------------------------------

CCxxPositioner* CCxxPositioner::NewL(TPositionModuleId aModuleId,
				     TInt aUpdateTimeOut, // in microseconds
				     TInt aMaxUpdateAge // in microseconds
				     )
{
  CCxxPositioner* obj = new (ELeave) CCxxPositioner(aModuleId,
						    aUpdateTimeOut,
						    aMaxUpdateAge);
  CleanupStack::PushL(obj);
  obj->ConstructL();
  CleanupStack::Pop();
  return obj;
}

CCxxPositioner::CCxxPositioner(TPositionModuleId aModuleId,
			       TInt aUpdateTimeOut, // in microseconds
			       TInt aMaxUpdateAge // in microseconds
			       ) : CActive(EPriorityStandard), 
				   iModuleId(aModuleId),
				   iUpdateTimeOut(aUpdateTimeOut),
				   iMaxUpdateAge(aMaxUpdateAge)
{
  CActiveScheduler::Add(this);
}

void CCxxPositioner::ConstructL()
{
  LEAVE_IF_ERROR_OR_SET_SESSION_OPEN(iPositionServer, iPositionServer.Connect());

  LEAVE_IF_ERROR_OR_SET_SESSION_OPEN(iPositioner, iPositioner.Open(iPositionServer, iModuleId));

  _LIT(KRequestor, "pytwink");
  User::LeaveIfError(iPositioner.SetRequestor(CRequestor::ERequestorService,
					      CRequestor::EFormatApplication, 
					      KRequestor));

  TPositionUpdateOptions updateOptions;
  updateOptions.SetAcceptPartialUpdates(EFalse);
  updateOptions.SetUpdateInterval(TTimeIntervalMicroSeconds(0)); // not periodic
  updateOptions.SetUpdateTimeOut(TTimeIntervalMicroSeconds(iUpdateTimeOut));
  updateOptions.SetMaxUpdateAge(TTimeIntervalMicroSeconds(iMaxUpdateAge));
  User::LeaveIfError(iPositioner.SetUpdateOptions(updateOptions));
}

CCxxPositioner::~CCxxPositioner()
{
  Cancel(); // safe when AO inactive as DoCancel not called
  SESSION_CLOSE_IF_OPEN(iPositioner);
  SESSION_CLOSE_IF_OPEN(iPositionServer);
  FreeCallback();
}

void CCxxPositioner::AskPosition(PyObject* aCallback)
{
  if (IsActive()) Cancel();
  FreeCallback();
  iCallback = aCallback;
  Py_INCREF(iCallback);
  iPositioner.NotifyPositionUpdate(iPositionInfo, iStatus);
  SetActive();
}

void CCxxPositioner::PythonCall(TInt errCode)
{
  PyEval_RestoreThread(PYTHON_TLS->thread_state);

  // if this fails, an exception should get set, and probably thrown
  // later in some other context; note that it seems that the
  // parameter must be a tuple (as always, such details are not easy
  // to find from the Python API reference).
  PyObject* arg = Py_BuildValue("(i)", errCode);
  if (arg)
    {
      PyObject* result = PyObject_CallObject(iCallback, arg);
      Py_DECREF(arg);
      Py_XDECREF(result);
      if (!result)
        {
          // Callbacks are not supposed to throw exceptions. Make sure
          // that the error gets noticed.
          PyErr_Clear();
          Panic(EPanicExceptionInCallback);
        }
    }

  PyEval_SaveThread();
}

void CCxxPositioner::RunL()
{
  TInt errCode = iStatus.Int();
  if (errCode != KErrNone) {
    PythonCall(errCode);
  } else {
    iPositionInfo.GetPosition(iPosition);
    if (Math::IsNaN(iPosition.Latitude()) ||
	Math::IsNaN(iPosition.Longitude())) {
      // We did not allow for partial "updates" or anything.
      PythonCall(KErrArgument);
    } else {
      // The requestor should use Position() to get the position.
      PythonCall(KErrNone);
    }
  }
}
  
// Actually this should never get called.
TInt CCxxPositioner::RunError(TInt aError)
{
  PythonCall(aError);
  return KErrNone;
}

void CCxxPositioner::DoCancel() 
{
  // Ignoring return value.
  iPositioner.CancelRequest(EPositionerNotifyPositionUpdate);
}

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
