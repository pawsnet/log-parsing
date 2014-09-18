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

import sys, getopt, re, time
from enum import Enum

class State(Enum):
    Invalid = 0
    Opening = 1
    Active = 2

class Session:
    def __init__(self, timestamp, username):
        self.timestamp = timestamp
        self.username = username
        self.state = State.Opening

    def __str__(self):
        if self.state == State.Active:
            rv = '%.0f, %s,  %s, %s,%s, "%s"' % (
                time.mktime(self.timestamp),
                self.username, self.locip, self.remip, self.rempt,
                time.asctime(self.timestamp)
            )
        return rv

def process(filenames):

    ts_format = "%Y %b %d %H:%M:%S"

    ip4_sre = "\d{1,3}[.]\d{1,3}[.]\d{1,3}[.]\d{1,3}"

    vpn_re = re.compile(".*openvpn.*")
    login_re = re.compile(
        ".*authentication succeeded for username '(?P<username>\w+)'.*")
    ipaddr_re = re.compile(
        ".*MULTI: Learn: (?P<locip>%s) -> (?P<username>\w+)/(?P<remip>%s):(?P<rempt>\d+)$"
        %(ip4_sre, ip4_sre))

    # ...client-instance exiting$
    # ...client-instance restarting$
    # ...TLS: tls_process: killed expiring key$
    # ...TLS Error: TLS handshake failed$
    # ...TLS: Username/Password authentication succeeded for username '...'

    ## initialise local state
    session = None

    for fn in filenames:
        with open(fn) as f:
            for line in map(lambda l:l.strip(), f.readlines()):

                ## ignore if not a vpn line
                if not vpn_re.match(line): continue

                ## what time is it?
                timestamp, line = line[:15], line[40:].strip()
                timestamp = time.strptime("2014 "+timestamp, ts_format)

                ## is this a session opening?
                m = login_re.match(line)
                if m:
                    username = m.group("username")
                    session = Session(timestamp, username)

                ## bail if we've no session in flight
                if not session: continue

                ## is this a session completing opening?
                m = ipaddr_re.match(line)
                if m:
                    ## barf if overlapping session
                    if session.username != m.group("username"): BARF
                    (session.locip, session.remip, session.rempt) = (
                        m.group("locip"), m.group("remip"), m.group("rempt"))

                    session.state = State.Active
                    print(session)

if __name__ == '__main__':

    global Verbose

    pairs = [ "h/help", "v/verbose", ]

    shortopts = "".join([ pair.split("/")[0] for pair in pairs ])
    longopts = [ pair.split("/")[1] for pair in pairs ]
    try: opts, args = getopt.getopt(sys.argv[1:], shortopts, longopts)
    except getopt.GetoptError as err: die_with_usage(err, 2)

    output = sys.stdout
    Verbose = True
    try:
        for o, a in opts:
            if o in ("-h", "--help"): die_with_usage()
            elif o in ("-v", "--verbose"): Verbose = True
            else: raise Exception("unhandled option")
    except Exception as err: die_with_usage(err, 3)

    process(args)
