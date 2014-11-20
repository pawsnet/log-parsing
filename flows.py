#!/usr/bin/env python3
#
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

import sys, bisect

def flags_to_string(f):
    return "%s%s%s%s%s%s%s%s" % (
        ((f & 1 << 0) >> 0) and "F" or ".",
        ((f & 1 << 1) >> 1) and "S" or ".",
        ((f & 1 << 2) >> 2) and "R" or ".",
        ((f & 1 << 3) >> 3) and "P" or ".",
        ((f & 1 << 4) >> 4) and "A" or ".",
        ((f & 1 << 5) >> 5) and "U" or ".",
        ((f & 1 << 6) >> 6) and "E" or ".",
        ((f & 1 << 7) >> 7) and "C" or ".",
        )

class Flow:
    def __init__(self, ts):
        self.first = ts
        self.last = ts
        self.sz = 0
        self.pkts = 0
        self.flags = 0
        self.urls = set()

    def __repr__(self):
        return "<%0.09f -- %0.09f, %d / %d, %s>" % (
            self.first, self.last, self.sz, self.pkts, flags_to_str(self.flags))

FLOWS    = {}
TIMEOUT  = 5*60                 # seconds
N = 0

def err(s):
    print(s, flush=True, file=sys.stderr)

def fopen(f):
    if f == "-": return sys.stdin
    else:
        return open(f)

if __name__ == '__main__':

    conns = sys.argv[1]

    with fopen(conns) as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                filename = line.split()[1]
                continue
            if line.startswith("frame.number"):
                continue

            try:
                fields = line.split(",")
                [ i, ts,
                  sip,spt_t,spt_u,
                  dip,dpt_t,dpt_u,
                  sz, flgs, host
                ] = fields[:11]
                url = ",".join(fields[11:])
            except:
                print(line, flush=True)
                raise

            ts = float(ts)
            sz = int(sz)

            url = "%s/%s" % (host, url)

            try: spt = int(spt_t + spt_u)
            except ValueError: spt = 0

            try: dpt = int(dpt_t + dpt_u)
            except ValueError: dpt = 0

            conn = (sip,spt, dip,dpt)

            ## determine packet direction
            outbound = sip.startswith("10.8")

            if sip.startswith("10.8") and dip.startswith("10.8"):
                err("%s@%0.09f %s.%d > %s.%d [%d]" % (
                    filename, ts, sip,spt, dip,dpt, sz))

                ## wtf? packets to self made it up tunneL? brief examination of
                ## traces up to 2014-11-19 indicate some (68B) are spotify
                ## related (initial payload "SpotUdp") and others (56B) are
                ## spurious ping replies. who knew...
                if sip == dip and spt == dpt: continue
                BARF

            if conn not in FLOWS: FLOWS[conn] = Flow(ts)
            flow = FLOWS[conn]

            diff = ts - FLOWS[conn].last
            if diff < TIMEOUT:
                flow.last = ts
                flow.sz += sz
                flow.pkts += 1
                if url != "/":
                    flow.urls.add(url)
                if len(flgs) > 0:
                    flow.flags |= int(flgs, 16)

            else:
                print("%d\t%0.09f\t%0.09f\t%0.09f\t%s.%d\t%s.%d\t%d\t%d\t%s\t%s" % (
                    N, flow.first, flow.last, flow.last-flow.first,
                    sip,spt, dip,dpt, flow.pkts, flow.sz,
                    flags_to_string(flow.flags),
                    " ".join((u for u in flow.urls))))

                N += 1
                del FLOWS[conn]
