#ifndef __application_config_h__
#define __application_config_h__

#include "common/platform_config.h"

// adapted from _LIT macro
#define _LIT_W(name,s) const static TLitC<sizeof(s)/2> name={sizeof(s)/2-1,s}

#define COMPONENT_NAME "pytwink"
#define COMPONENT_NAME_W L"pytwink"

#define COMPONENT_NAME_LIT8(ident) _LIT8(ident, COMPONENT_NAME)
#define COMPONENT_NAME_LIT(ident) _LIT_W(ident, COMPONENT_NAME_W)

#define PRIMARY_LOG_FILENAME "pytwink_log.txt"

// Invoked internally by logging.cpp.
#define DEFINE_LOG_FILE_DIR _LIT(KLogFileDir, "pytwink");

// Invoked internally by logging.cpp.
#define DEFINE_ASSERT_LOG_FILENAME _LIT(KAssertLogFile, "pytwink_assert.txt");

// Invoked internally by panic.cpp.
#define DEFINE_PANIC_CATEGORY COMPONENT_NAME_LIT(KPanicCategory)

#endif /* __application_config_h__ */

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
