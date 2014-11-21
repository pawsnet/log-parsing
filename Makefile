# Copyright (c) 2014, Richard Mortier <mort@cantab.net>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

help:
	@egrep "^.*: " Makefile | grep -v "@egrep"

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

process-paws1-selfsignups: # PAWS1 self-signups
	egrep -h \
	  '"GET /secure-cgi/(consent.cgi|su.cgi|vpn/instructions.cgi).*HTTP/1.1" 200'\
	  data/paws1-signups/httpdlogs/ssl_access_log*  >| data/paws1-signups/ssl-accesses
	egrep -h \
	  'authentication failure for .* Password Mismatch'\
	  data/paws1-signups/httpdlogs/ssl_error_log*  >| data/paws1-signups/ssl-errors
	./self-signups.py $(VERBOSE) \
	  data/paws1-signups/ssl-{accesses,errors}

process-paws2-vpn: # PAWS2 citizen usage
	./vpn-users.py $(VERBOSE) \
	  data/paws2-vpn/messages-* data/paws2-vpn/messages | \
	  sort -n -t "," -k 1,2 >| data/paws2-vpn/vpn-logins$(VERBOSE).csv

process-paws2-uptimes: # PAWS2 router availability
	 ./availaility.py RAW
	sort -n -t" " -k 3 logdata.clean.csv >| \
	  data/paws2-uptimes/logdata.clean.sorted.csv
	./availaility.py COOKED >| data/paws2-uptimes/uptimes.csv

process-paws2-pcap: # Process PCAP files, remotely \
	process-paws2-pcap-names \
	process-paws2-pcap-connections \
	process-paws2-pcap-urls \

process-paws2-pcap-names: # Extract URLs from PCAPs
	$(SSHPAWS) -t \
	  '$(RM) paws2-names.txt;\
		for pcap in $$(ls -1tr ~paws/tcpdump/tun0_*pcap*) ; do \
		echo "# $${pcap}" ;\
		/usr/sbin/tshark -r $${pcap} \
		  -2 -T fields -R "udp.srcport==53" \
		  -e frame.number -e frame.time_epoch -e ip.src -e ip.dst \
		  -e dns.qry.name -e dns.resp.name -e dns.resp.addr \
		   -E header=y -E separator=, -E quote=n -E occurrence=f ;\
	  done >> paws2-names.txt'
	scp paws@paws-server:~/paws2-names.txt data/paws2-pcap

process-paws2-pcap-tagging: # Tag extracted DNS names
	grep -v "^#" data/paws2-pcap/paws2-names.txt |\
		cut -d"," -f 5 | sort | uniq -c | sort -rn | tr -s " " |\
		./dns-tagging.coffee >| data/paws2-pcap/paws2-names-tagged.txt

process-paws2-pcap-connections: # Extract conversation data
	$(SSHPAWS) -t \
	  '$(RM) paws-connections.txt;\
		for pcap in $$(ls -1tr ~paws/tcpdump/tun0_*pcap*) ; do \
		echo "# $${pcap}" ;\
		/usr/sbin/tshark -r $${pcap} \
		  -2 -T fields \
		  -e frame.number -e frame.time_epoch \
		  -e ip.src -e tcp.srcport -e udp.srcport \
		  -e ip.dst -e tcp.dstport -e udp.dstport \
		  -e ip.len -e tcp.flags \
		  -e http.host -e http.request.uri \
		  -E header=y -E separator=, -E quote=n -E occurrence=f ;\
	  done >> paws2-connections.txt'
	scp paws@paws-server:~/paws2-connections.txt data/paws2-pcap

process-paws2-pcap-flows: # Convert conversations to flows
	./flows.py data/paws2-pcap/paws2-connections.txt >| \
		data/paws2-pcap/paws2-flows.txt

process-paws2-pcap-tag-flows: # Tag flows
	./connection-tagging.py \
		data/paws2-pcap/paws2-{names-tagged,names,flows}.txt >| \
		data/paws2-pcap/paws2-flows-tagged.txt

process-paws2-pcap-urls: # Extract HTTP URL data
	$(SSHPAWS) -t \
	   '$(RM) paws2-urls.txt; \
		for pcap in $$(ls -1tr ~paws/tcpdump/tun0_*pcap*) ; do \
		echo "# $${pcap}" ;\
		/usr/sbin/tshark -r $${pcap} -R "http.response or http.request" \
		  -2 -T fields \
		  -e frame.time_epoch \
		  -e ip.src -e tcp.srcport \
		  -e ip.dst -e tcp.dstport \
		  -e http.host -e http.request.uri \
		  -e http.content_type -e http.content_length \
		  -e http.location -e http.referer \
		  -E header=y -E separator="|" -E quote=n -E occurrence=f ;\
	  done >> paws2-urls.txt'
	scp paws@paws-server:~/paws2-urls.txt data/paws2-pcap

clean: # remove droppings
	$(RM) data/paws2-vpn/vpn-logins*.csv data/paws2-uptimes/uptimes.csv
