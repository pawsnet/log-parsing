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

all: help
clean:
	$(RM) data/paws2-vpn/vpn-logins*.csv data/paws2-uptimes/uptimes.csv
	$(RM) dns-tagging.js

paws2-vpn: paws2-vpn-fetch # PAWS2 citizen usage
	./vpn-users.py $(VERBOSE) \
	  data/paws2-vpn/messages-* data/paws2-vpn/messages \
	  | sort -n -t "," -k 1,2 \
	  >| data/paws2-vpn/vpn-logins$(VERBOSE).csv
	scp data/paws2-vpn/vpn-logins.csv mort@paws-server:~
	$(SSH) -t "sudo mv vpn-logins.csv /var/www/secure-html/timeline"

paws2-vpn-fetch: # Fetch PAWS2 VPN logs
	mkdir -p data/paws2-vpn
	$(SSH) -t \
	  "sudo cp /var/log/messages* ~/ && sudo chown $(USER):$(USER) ~/messages*"
	$(SSH) \
	  tar czvf - /home/$(USER)/messages* | \
	  ( cd data/paws2-vpn ; tar xvzf - --strip-components 2 )
	$(SSH) \
	  $(RM) ~/messages*

paws2-uptimes: paws2-uptimes-fetch # PAWS2 router availability
	./availaility.py data/paws2-uptimes/observations.txt \
	  | sort -n -t "," -k 1,2 \
	  >| data/paws2-uptimes/uptimes.csv
	scp data/paws2-uptimes/uptimes.csv mort@paws-server:~
	$(SSH) -t "sudo mv uptimes.csv /var/www/secure-html/timeline"

paws2-uptimes-fetch: # Fetch PAWS2 uptime observations
	mkdir -p data/paws2-uptimes
	$(SSH) -t \
	  "$(RM) o o.bz2 \
	  && psql -A -q -U paws -h 127.0.0.1 -p 5432 -d paws_mgmt -c \"SELECT id,ip,EXTRACT(epoch from date_trunc('second', date_seen)) FROM devices_log ORDER BY date_seen;\" > o \
	  && bzip2 -v9 o"
	scp mort@paws-server:~/o.bz2 data/paws2-uptimes/observations.txt.bz2
	cd data/paws2-uptimes && $(RM) observations.txt && \
	  bunzip2 -v observations.txt.bz2
	$(SSH) -t "$(RM) ~/o.bz2"

paws2-pcap: \ # Process PCAP files, remotely
	paws2-pcap-names paws2-pcap-tag-names \
	paws2-pcap-flows paws2-pcap-tag-flows \

paws2-pcap-names: # Extract URLs from PCAPs
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

paws2-pcap-tag-names: # Tag extracted DNS names
	grep -v "^#" data/paws2-pcap/paws2-names.txt |\
		cut -d"," -f 5 | sort | uniq -c | sort -rn | tr -s " " |\
		./dns-tagging.coffee >| data/paws2-pcap/paws2-names-tagged.txt

paws2-pcap-flows: # Convert conversations to flows
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
	./extract-flows.py data/paws2-pcap/paws2-connections.txt >| \
		data/paws2-pcap/paws2-flows.txt

paws2-pcap-tag-flows: # Tag flows
	./tag-flows.py \
		data/paws2-pcap/paws2-{names-tagged,names,flows}.txt >| \
		data/paws2-pcap/paws2-flows-tagged.txt

paws2-pcap-urls: # Extract HTTP URL data
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

paws1-selfsignups: # PAWS1 self-signups
	egrep -h \
	  '"GET /secure-cgi/(consent.cgi|su.cgi|vpn/instructions.cgi).*HTTP/1.1" 200'\
	  data/paws1-signups/httpdlogs/ssl_access_log*  >| data/paws1-signups/ssl-accesses
	egrep -h \
	  'authentication failure for .* Password Mismatch'\
	  data/paws1-signups/httpdlogs/ssl_error_log*  >| data/paws1-signups/ssl-errors
	./self-signups.py $(VERBOSE) \
	  data/paws1-signups/ssl-{accesses,errors}
