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

Tags = {}
Names = {}

def dbg(s):
    print(s, file=sys.stderr)

def fopen(f):
    if f == "-": return sys.stdin
    else:
        return open(f)

if __name__ == '__main__':

    [tags, names, conns] = sys.argv[1:4]

    with fopen(tags) as f:
        for line in f:
            line = line.strip()
            _, name, tags = line.split("|")
            tags = tags.split(",")
            Tags[name] = tags

    with fopen(names) as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                filename = line.split()[1]
                print("# %s" % filename)
                continue

            ni, ts, ns, qip, qname, aname, aip = line.split(",")

            if qip not in Names: Names[qip] = {}
            if aip not in Names[qip]: Names[qip][aip] = set()
            Names[qip][aip].add(qname)
            Names[qip][aip].add(aname)

    with fopen(conns) as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                filename = line.split()[1]
                continue

            try:
                fields = line.split(",")
                [i, ts, sip,spt,_, dip,dpt,_, sz, flgs, host] = fields[:11]
                url = ",".join(fields[11:])
            except:
                print(line, flush=True)
                raise

