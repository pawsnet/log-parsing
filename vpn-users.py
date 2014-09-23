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

TIMEOUT = 10 * 60

class State(Enum):
    Invalid = 0
    Opening = 1
    Active = 2

class Session:
    def __init__(self, open_ts, username):
        self.open_ts = self.refresh_ts = open_ts
        self.username = username
        self.state = State.Opening

    def __str__(self):
        if self.state == State.Active:
            rv = '%.0f,%.0f,%.0f, %s,  %s, %s,%s, "%s","%s"' % (
                time.mktime(self.open_ts), time.mktime(self.refresh_ts),
                time.mktime(self.refresh_ts)-time.mktime(self.open_ts),
                self.username, self.locip, self.remip, self.rempt,
                time.asctime(self.open_ts), time.asctime(self.refresh_ts)
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
    timeout_re = re.compile(
        "(?P<username>\w+)/(?P<remip>%s):(?P<rempt>\d+) \[\w+\] Inactivity timeout" % (ip4_sre,))
    clientexit_re = re.compile(
        "(?P<username>\w+)/(?P<remip>%s):(?P<rempt>\d+) SIGTERM\[soft,remote-exit\] received, client-instance exiting" % (ip4_sre,))

    # ...client-instance exiting$
    # ...client-instance restarting$
    # ...TLS: tls_process: killed expiring key$
    # ...TLS Error: TLS handshake failed$
    # ...TLS: Username/Password authentication succeeded for username '...'

    ## initialise local state
    session = None
    sessions = {}

    for fn in filenames:
        with open(fn) as f:
            for line in map(lambda l:l.strip(), f.readlines()):

                ## ignore if not a vpn line
                if not vpn_re.match(line): continue

                ## what time is it?
                timestamp, line = line[:15], line[40:].strip()
                timestamp = time.strptime("2014 "+timestamp, ts_format)

                ## is this a session completing opening?
                m = ipaddr_re.match(line)
                if m:
                    username = m.group("username")
                    if username not in sessions: continue
                    session = sessions[username]

                    (locip, remip, rempt) = (
                        m.group("locip"), m.group("remip"), m.group("rempt"))

                    if session.state != State.Active:
                        session.locip = locip
                        session.remip = remip
                        session.rempt = rempt
                        session.state = State.Active

                    else:
                        session.refresh_ts = timestamp
                        if Verbose:
                            if (locip, remip, rempt) != (
                                    session.locip, session.remip, session.rempt
                            ):
                                ## change of remote port; new device?
                                print(session, ", new-device")
                                session.locip = locip
                                session.remip = remip
                                session.rempt = rempt
                                session.open_ts = timestamp
                                session.refresh_ts = timestamp

                    sessions[username] = session
                    continue

                ## is this a session timing out?
                m = timeout_re.match(line)
                if m:
                    username = m.group("username")
                    if username not in sessions: continue
                    session = sessions[username]

                    ## best estimate we have for when session went idle
                    session.refresh_ts = timestamp ## time.gmtime(time.mktime(timestamp) - TIMEOUT)

                    print(session, ", timeout")
                    del sessions[username]
                    continue

                ## is this a session just closing?
                m = clientexit_re.match(line)
                if m:
                    username = m.group("username")
                    if username not in sessions: continue
                    session = sessions[username]

                    ## best estimate we have for when session went idle
                    session.refresh_ts = timestamp ## time.gmtime(time.mktime(timestamp) - TIMEOUT)
                    print(session, ", client-exit")
                    del sessions[username]
                    continue

                ## is this a new session?
                m = login_re.match(line)
                if m:
                    username = m.group("username")
                    if username in sessions: session = sessions[username]
                    else:
                        session = Session(timestamp, username)
                        sessions[username] = session

    for session in sessions.values():
        session.refresh_ts = timestamp
        print(session, ", eof")

if __name__ == '__main__':

    global Verbose

    pairs = [ "h/help", "v/verbose", ]

    shortopts = "".join([ pair.split("/")[0] for pair in pairs ])
    longopts = [ pair.split("/")[1] for pair in pairs ]
    try: opts, args = getopt.getopt(sys.argv[1:], shortopts, longopts)
    except getopt.GetoptError as err: die_with_usage(err, 2)

    output = sys.stdout
    Verbose = False
    try:
        for o, a in opts:
            if o in ("-h", "--help"): die_with_usage()
            elif o in ("-v", "--verbose"): Verbose = True
            else: raise Exception("unhandled option")
    except Exception as err: die_with_usage(err, 3)

    process(args)
