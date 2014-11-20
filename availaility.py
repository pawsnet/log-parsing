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

import sys, time
from datetime import datetime, timezone

DIR = "data/paws2-uptimes"
TIMEOUT = 600

if __name__ == '__main__':

    if sys.argv[1] == "RAW":
        filename = DIR+"/logdata.csv"
        outputf = open(DIR+"/logdata.clean.csv", "w")
        with open(filename) as f:
            for line in [ l.strip() for l in f.readlines()[1:] ]:
                (pawsid, _, ipaddr, observed) = line.split(",")

                try:
                    observed = datetime.strptime(observed, "%Y-%m-%d %H:%M:%S.%f")
                    timestamp = observed.replace(tzinfo=timezone.utc).timestamp()
                except ValueError:
                    observed = datetime.strptime(observed, "%Y-%m-%d %H:%M:%S")
                    timestamp = observed.replace(tzinfo=timezone.utc).timestamp()

                print("%s, %s, %0.6f" % (pawsid, ipaddr, timestamp),
                      file=outputf)

    elif sys.argv[1] == "COOKED":
        ## after
        ## $ sort -n -t" " -k 3 logdata.clean.csv > logdata.clean.sorted.csv
        obs = {}
        filename = DIR+"/logdata.clean.sorted.csv"
        with open(filename) as f:
            for line in [ l.strip() for l in f.readlines()[1:] ]:
                (pawsid, ipaddr, timestamp) = line.split(",")
                timestamp = float(timestamp)
                now = timestamp

                if pawsid not in obs: obs[pawsid] = [timestamp, timestamp]
                ob = obs[pawsid]
                gap = timestamp - ob[1]

                if gap <= TIMEOUT:
                    ob[1] = timestamp
                    if ob[1]-ob[0] < 0:
                        print(ob, line)
                        BARF
                elif gap > TIMEOUT:
                    print("%s, %0.6f, %0.6f" % (pawsid, ob[0], ob[1]-ob[0]))
                    obs[pawsid] = [timestamp, timestamp]

            for pawsid in obs:
                ob = obs[pawsid]
                print("%s, %0.6f, %0.6f" % (pawsid, ob[0], ob[1]-ob[0]))
