# The default heap size of max 4M is not enough for our gallery, so we are using 16M instead.

# If not using an unhacked version of ensymble, one requires the --unsign switch for the devsis_unsigned rule (available from v0.28).

# The auto installer Makefile shows how to build a standalone app for PyS60v2.

# Note that a self32-signed application in this case is just fine, but on older phones we must still use DevCert signed SIS files. We can use the same set of caps for the application itself regardless, though.

CERT := dev
DEVICE := default
DRIVE := e
KIT := s60_30
PYC :=

MAJOR_VERSION := 3
MINOR_VERSION := 1
APP_VERSION := $(MAJOR_VERSION).$(MINOR_VERSION).0
BASENAME := tpytwink
ICON := icon.svgz
PROJECT_NAME := tpytwink
SHORTCAPTION := Tpytwink,Tpytwink
LONGCAPTION := TestPytwink,TestPytwink
UID3 := e8430035
DEFAULT_PY := tpytwink_default.py
MAIN_PY := tpytwink_main.py
PY_LIBS := tpytwink_engine.py tpytwink_gallery_screen.py tpytwink_list_screen.py tpytwink_logo_screen.py tpytwink_utils.py
PYC_LIBS := $(patsubst %,%c,$(MAIN_PY) $(PY_LIBS))
BYTE_COMPILE := $(if $(PYC),true,false)

ifeq ($(CERT),unsigned)
  DIST_CERT := dev
  VARIANT := unsigned
  CERTINFO := --unsigned
else
  DIST_CERT := $(CERT)
  VARIANT := $(CERT)
  CERTINFO := `symbian-config -e $(CERT)`
endif

ifeq ($(DIST_CERT),dev)
  #CAPS_SPEC := --caps=LocalServices+NetworkServices+ReadUserData+UserEnvironment+WriteUserData+Location+PowerMgmt+ProtServ+ReadDeviceData+SurroundingsDD+SwEvent+TrustedUI+WriteDeviceData
  CAPS_SPEC := --caps=ReadUserData+WriteUserData+NetworkServices+LocalServices+UserEnvironment+Location
else ifeq ($(DIST_CERT),self30)
  CAPS_SPEC := --caps=ReadUserData+WriteUserData+NetworkServices+LocalServices+UserEnvironment
else ifeq ($(DIST_CERT),self32)
  CAPS_SPEC := --caps=ReadUserData+WriteUserData+NetworkServices+LocalServices+UserEnvironment+Location
else
  $(error unsupported DIST_CERT $(DIST_CERT))
endif

# The cert used does not really matter, but giving a cert spec to avoid an ensymble warning about an 'insecure' cert.
ENSYMBLE_CERTINFO := `symbian-config -e self`

APPOPT := $(ENSYMBLE_CERTINFO) $(CAPS_SPEC) --uid=0x$(UID3) --heapsize=4k,16M --appname=$(BASENAME) --version=$(APP_VERSION) --lang=EN,FI --icon=$(ICON) "--shortcaption=$(SHORTCAPTION)" "--caption=$(LONGCAPTION)" "--vendor=HIIT,HIIT" --encoding=utf8,ascii --verbose $(DEFAULT_PY) tmp.sis

ENSYMBLE := ensymble

default : sis

skeleton-sis :
	$(ENSYMBLE) py2sis $(APPOPT)

unpack-skeleton :
	-rm -r skeleton
	sisinfo -f tmp.sis -e skeleton

ROOTDIR := ../..

# The makesis tool insists on a .sis extension, so we rename here. We also select the desired variant here (cert, etc.), so the .pkg file can be simple.
copy-deps :
	-rm -r deps
	mkdir deps
	cp -ai $(ROOTDIR)/simplejson/simplejson.sisx deps/simplejson.sis
	cp -ai $(ROOTDIR)/fnmatch-python/fnmatch-pys60v1_self.sisx deps/fnmatch.sis
	cp -ai $(ROOTDIR)/miso/build/$(KIT)_py1_$(CERT)/miso.sisx deps/miso.sis
	cp -ai $(ROOTDIR)/pyinbox/build/$(KIT)_$(CERT)/pyinbox.sisx deps/pyinbox.sis
	cp -ai $(ROOTDIR)/pynewfile/build/$(KIT)_$(CERT)/pynewfile.sisx deps/pynewfile.sis
	cp -ai $(ROOTDIR)/pyaosocket/build/$(KIT)_$(CERT)/pyaosocket.sisx deps/pyaosocket.sis
	cp -ai $(ROOTDIR)/pybtswitch/build/$(KIT)_$(CERT)/pybtswitch.sisx deps/pybtswitch.sis
	cp -ai $(ROOTDIR)/pytwink/build/$(KIT)_$(CERT)/pytwink.sisx deps/pytwink.sis

PKGIN_FILE := template.pkg
PKG_FILE := $(BASENAME).pkg
RUBY_STRLIST := BASENAME MAJOR_VERSION MINOR_VERSION PROJECT_NAME UID3
RUBY_VARLIST := BYTE_COMPILE
RUBY_EXPORTS := $(foreach name,$(RUBY_STRLIST),$(name) = "$($(name))";) $(foreach name,$(RUBY_VARLIST),$(name) = $($(name));)

pkg :
	ruby -e '$(RUBY_EXPORTS) require "erb"; load("tools/utils.rb"); puts(ERB.new(File.read("$(PKGIN_FILE)")).result(binding()))' > $(PKG_FILE)

BUILT_SIS := $(BASENAME)_$(VARIANT).sis

sis : $(and $(PYC), compile) skeleton-sis unpack-skeleton pkg
	in-gnupoc-env $(KIT) do-sis-signing.rb --makesis --signsis --cert $(CERT) -o $(BUILT_SIS) -i $(PKG_FILE)

# Note that this requires python2.2, which modern Linux distros do not have.
# So you may have to build your own copy from source.
compile :
	ruby tools/byte-compile.rb $(MAIN_PY) $(PY_LIBS)

-include local/custom.mk

clean :
	-rm *~ *.pyc *.sis tpytwink.pkg
	-rm -r skeleton
