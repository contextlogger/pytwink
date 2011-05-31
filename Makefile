CERT := dev
KIT := s60_30

BASENAME := pytwink
VERSION := 3.01

default : bin

-include local/custom.mk

bin :
	sake --trace cert=$(CERT) kits=$(KIT)

bin-all :
	sake all release kits=s60_20
	sake all release kits=s60_30 cert=self
	sake all release kits=s60_30 cert=dev

