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

SHELL = /usr/bin/env bash
SSH = ssh $(USER)@paws-server
SSHPAWS = ssh paws@paws-server

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

process: process-paws2-vpn process-paws2-uptimes process-paws2-pcap

process-paws2-vpn: # PAWS2 citizen usage
	./vpn-users.py $(VERBOSE) \
	  data/paws2-vpn/messages-* data/paws2-vpn/messages | \
	  sort -n -t "," -k 1,2 >| data/paws2-vpn/vpn-logins$(VERBOSE).csv

process-paws2-uptimes: # PAWS2 router availability
	 ./availaility.py RAW
	sort -n -t" " -k 3 logdata.clean.csv >| \
	  data/paws2-uptimes/logdata.clean.sorted.csv
	./availaility.py COOKED >| data/paws2-uptimes/uptimes.csv

process-paws2-pcap: # Extract URLs from PCAPs
	$(RM) data/paws2-pcap/names
	$(SSHPAWS) -t \
	  'for pcap in $$(ls -1tr ~paws/tcpdump/tun0_*pcap*) ; do \
		echo "# $${pcap}" ;\
		/usr/sbin/tshark -r $${pcap} \
		  -2 -T fields -R "udp.srcport==53" \
		  -e frame.number -e frame.time_epoch -e ip.src -e ip.dst \
		  -e dns.qry.name -e dns.resp.name -e dns.a \
		  -E separator=, -E quote=n -E occurrence=f ;\
	  done' \
	>> data/paws2-pcap/names

	$(RM) data/paws2-pcap/urls
	$(SSHPAWS) -t \
	  'for pcap in $$(ls -1tr ~paws/tcpdump/tun0_*pcap*) ; do \
		echo "# $${pcap}" ;\
		/usr/sbin/tshark -r $${pcap} \
		  -2 -T fields \
		  -e frame.number -e frame.time_epoch \
		  -e ip.src -e tcp.srcport -e udp.srcport \
		  -e ip.dst -e tcp.dstport -e udp.dstport \
		  -e http.host -e http.request.uri \
		  -E header=y -E separator=, -E quote=n -E occurrence=f ;\
	  done' \
	>> data/paws2-pcap/urls

clean: # remove droppings
	$(RM) data/paws2-vpn/vpn-logins*.csv data/paws2-uptimes/uptimes.csv
