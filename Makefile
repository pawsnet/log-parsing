# Copyright (C) 2014 Richard Mortier <mort@cantab.net>.  All Rights
# Reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
# USA.

help:
	@egrep "^.*: " Makefile

SSH = ssh $(USER)@paws-server

all: fetch process

fetch: fetch-paws2-vpn

fetch-paws2-vpn: # Fetch PAWS2 VPN logs
	mkdir -p data
	$(SSH) -t \
	  "sudo cp /var/log/messages* ~/ && sudo chown $(USER):$(USER) ~/messages*"
	$(SSH) \
	  tar czvf - /home/$(USER)/messages* | \
	  ( cd data/paws2-vpn ; tar xvzf - --strip-components 2 )
	$(SSH) \
	  $(RM) ~/messages*

process: process-paws2-vpn process-paws2-uptimes

process-paws2-vpn: # PAWS2 citizen usage
	./vpn-users.py $(VERBOSE) \
	  data/paws2-vpn/messages-* data/paws2-vpn/messages | \
	  sort -n -t "," -k 1,2 >| data/paws2-vpn/vpn-logins$(VERBOSE).csv

process-paws2-uptimes: # PAWS2 router availability
	 ./availaility.py RAW
	sort -n -t" " -k 3 logdata.clean.csv >| \
	  data/paws2-uptimes/logdata.clean.sorted.csv
	./availaility.py COOKED >| data/paws2-uptimes/uptimes.csv

clean: # remove droppings
	$(RM) data/paws2-vpn/vpn-logins*.csv data/paws2-uptimes/uptimes.csv
