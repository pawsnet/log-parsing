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

import sys

if __name__ == '__main__':

    OBS = {}
    TIMEOUT = 600

    filename = sys.argv[1]
    with open(filename) as f:
        for line in f:
            if not line.startswith("OW"): continue
            pawsid, ip, ts = map(lambda l: l.strip(), line.strip().split("|"))

            ts = float(ts)

            if pawsid not in OBS: OBS[pawsid] = [ts, ts]
            ob = OBS[pawsid]

            gap = ts - ob[1]
            if gap > TIMEOUT:
                print("%s, %0.0f, %0.0f" % (pawsid, ob[0], ob[1]-ob[0]))
                del OBS[pawsid]
            else:
                ob[1] = ts
                if ob[1] - ob[0] < 0:
                    print("ERR: "+line)
                    BARF
