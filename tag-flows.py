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

TAGS = {}
NAMES = {}

def err(s):
    print(s, flush=True, file=sys.stderr)

def fopen(f):
    if f == "-": return sys.stdin
    else:
        return open(f)

if __name__ == '__main__':

    [tags, names, flows] = sys.argv[1:4]

    with fopen(tags) as f:
        for line in f:
            _, name, tags = line.strip().split("|")

            tags = tags.split(",")
            name = name.strip()
            if len(name) > 0:
                TAGS[name] = set(
                    tag.strip() for tag in tags if len(tag.strip()) > 0)

    with fopen(names) as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                filename = line.split()[1]
                err("# %s" % filename)
                continue

            ni, ts, ns, qip, qname, aname, aip = line.split(",")

            if qip not in NAMES: NAMES[qip] = {}
            if aip not in NAMES[qip]: NAMES[qip][aip] = set()
            NAMES[qip][aip].add(qname)
            NAMES[qip][aip].add(aname)

    with fopen(flows) as f:
        for line in f:
            try:
                fields = line.strip("\n").split("\t")
                [ i, start,end,duration,
                  src,dst, pkts,bytes, flags, urls ] = fields
            except:
                err(line, flush=True)
                raise

            if src.startswith("10.8"):
                qip = ".".join(src.split(".")[:4])
                aip = ".".join(dst.split(".")[:4])
            else:
                aip = ".".join(src.split(".")[:4])
                qip = ".".join(dst.split(".")[:4])

            names = set()
            tags = set()
            if qip in NAMES:
                if aip in NAMES[qip]:
                    names = NAMES[qip][aip]

            for n in names:
                if n in TAGS: tags |= TAGS[n]

            print("%s\t%s\t%s" % (
                "\t".join(fields), ";".join(names), ";".join(tags)))
