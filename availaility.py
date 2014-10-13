#!/usr/bin/env python3
#
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

import sys, time
from datetime import datetime, timezone

DIR = "data/paws2-uptimes"
TIMEOUT = 600

if __name__ == '__main__':

    if sys.argv[1] == "RAW":
        filename = DIR+"logdata.csv"
        outputf = open(DIR+"logdata.clean.csv", "w")
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
        filename = DIR+"logdata.clean.sorted.csv"
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
