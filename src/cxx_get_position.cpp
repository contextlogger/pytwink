#include "cxx_get_position.hpp"

static void GetPositionOnceL(RPositioner& positioner,
			     TPosition& position,
			     TRequestStatus& status)
{
  TPositionInfo positionInfo;
  positioner.NotifyPositionUpdate(positionInfo, status);
  //positioner.GetLastKnownPosition(positionInfo, status);
  User::WaitForRequest(status);
  if (status != KErrNone) {
    User::Leave(status.Int());
  } else {
    positionInfo.GetPosition(position);
  }
}

void GetCurrentPositionL(TPosition& position,
			 TPositionModuleId aModuleId)
{
  RPositionServer positionServer;
  User::LeaveIfError(positionServer.Connect());
  CleanupClosePushL(positionServer);
  RPositioner positioner;
  User::LeaveIfError(positioner.Open(positionServer, aModuleId));
  CleanupClosePushL(positioner);

  _LIT(KRequestor, "pytwink");
  User::LeaveIfError(positioner.SetRequestor(CRequestor::ERequestorService,
					     CRequestor::EFormatApplication, 
					     KRequestor));

  TPositionUpdateOptions updateOptions;
  updateOptions.SetAcceptPartialUpdates(EFalse);
  updateOptions.SetUpdateInterval(TTimeIntervalMicroSeconds(0)); // not periodic
  updateOptions.SetUpdateTimeOut(TTimeIntervalMicroSeconds(15000000));
  updateOptions.SetMaxUpdateAge(TTimeIntervalMicroSeconds(30000000));
  User::LeaveIfError(positioner.SetUpdateOptions(updateOptions));

  TRequestStatus status;
  GetPositionOnceL(positioner, position, status);
#if 0
  if (Math::IsNaN(position.Latitude()) ||
      Math::IsNaN(position.Longitude())) {
    // Try again.
    GetPositionOnceL(positioner, position, status);
  }
#else
  if (Math::IsNaN(position.Latitude()) ||
      Math::IsNaN(position.Longitude())) {
    // We did not allow for partial "updates" or anything.
    User::Leave(KErrArgument);
  }
#endif
  CleanupStack::PopAndDestroy(&positioner);
  CleanupStack::PopAndDestroy(&positionServer);
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
