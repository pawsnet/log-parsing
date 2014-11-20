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

import sys, getopt, re, time, os
from enum import Enum

TIMEOUT = 10 * 60
IP4_SRE = "\d{1,3}[.]\d{1,3}[.]\d{1,3}[.]\d{1,3}"

class State(Enum):
    Invalid = 0
    Opening = 1
    Active = 2

def dump_session(username, sessions, reason):
    session = sessions[username]
    if Verbose: print(session, ",", reason)
    else:
        print(session)
    del sessions[username]
    return sessions

class Session:
    def __init__(self, open_ts, username):
        self.open_ts = self.refresh_ts = open_ts
        self.username = username
        self.state = State.Opening

    def __str__(self):
        if self.state == State.Active:
            rv = '%s, %.0f, %0.f' % (
                self.username, time.mktime(self.open_ts),
                time.mktime(self.refresh_ts)-time.mktime(self.open_ts),
            )
            if Verbose:
                rv += ',  %s, %s,%s, "%s","%s"' % (
                    self.locip, self.remip, self.rempt,
                    time.asctime(self.open_ts), time.asctime(self.refresh_ts)
                )
            return rv

def process_details(fn, sessions={}):
    # Acct-Session-Id = "xxxxxxxxxxxx"
    sessionid_re = re.compile('Acct-Session-Id = "(?P<sessionid>[0-9A-F]+)"')

    # User-Name = "xxxxx"
    username_re = re.compile('User-Name = "(?P<username>\w)"')

    # Acct-Status-Type = Start|Stop
    # Calling-Station-Id = ipaddr-of-ap
    remip_re = re.compile('Calling-Station-Id = "(?P<remip>%s)"' % (IP4_SRE,))

    # Frame-IP-Address = ipaddr-in-traces
    locip_re = re.compile('Frame-IP-Address = "(?P<locip>%s)"' % (IP4_SRE,))

    ## stop only
    # Timestamp = starttime-as-unixt
    ts_re = re.compile("Timestamp = (?P<timestamp>\d+)")

    # Acct-Output-Octets, Acct-Input-Octets, Acct-Session-Time = secs
    # end == \n\n
    rs_re = re.compile("^$")

    with open(fn) as f:
        for line in map(lambda l:l.strip(), f.readlines()):

            if rs_re.match(line):
                session = Session(timestamp, username)

            m = ts_re.match(line)
            if m:
                timestamp = time.gmtime(m.group("timestamp"))

            m = sessionid_re.match(line)
            if m:
                sessionid = m.group("sessionid")

            m = username_re.match(line)
            if m:
                username = m.group("username")

            m = remip_re.match(line)
            if m:
                remip = m.group("remip")

            m = locip_re.match(line)
            if m:
                locip = m.group("locip")

def process_messages(fn, sessions={}):

    ts_format = "%Y %b %d %H:%M:%S"

    vpn_re = re.compile(".*openvpn.*")
    login_re = re.compile(
        ".*authentication succeeded for username '(?P<username>\w+)'.*")
    ipaddr_re = re.compile(
        ".*MULTI: Learn: (?P<locip>%s) -> (?P<username>\w+)/(?P<remip>%s):(?P<rempt>\d+)$"
        %(IP4_SRE, IP4_SRE))
    timeout_re = re.compile(
        "(?P<username>\w+)/(?P<remip>%s):(?P<rempt>\d+) \[\w+\] Inactivity timeout" % (IP4_SRE,))
    clientexit_re = re.compile(
        "(?P<username>\w+)/(?P<remip>%s):(?P<rempt>\d+) SIGTERM\[soft,remote-exit\] received, client-instance exiting" % (IP4_SRE,))

    # ...client-instance exiting$
    # ...client-instance restarting$
    # ...TLS: tls_process: killed expiring key$
    # ...TLS Error: TLS handshake failed$
    # ...TLS: Username/Password authentication succeeded for username '...'

    ## initialise local state
    session = None

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
                    if (locip, remip, rempt) != (
                            session.locip, session.remip, session.rempt
                    ):
                        ## change of remote port; new device?
                        if Verbose: print(session, ", new-device")
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
                session.refresh_ts = timestamp
                sessions = dump_session(username, sessions, "timeout")
                continue

            ## is this a session just closing?
            m = clientexit_re.match(line)
            if m:
                username = m.group("username")
                if username not in sessions: continue

                session = sessions[username]
                ## best estimate we have for when session went idle
                session.refresh_ts = timestamp

                sessions = dump_session(username, sessions, "client-exit")
                continue

            ## is this a new session?
            m = login_re.match(line)
            if m:
                username = m.group("username")
                if username in sessions: session = sessions[username]
                else:
                    session = Session(timestamp, username)
                    sessions[username] = session

    return sessions

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

    sessions = {}
    for filename in args:
        fn = os.path.basename(filename)
        if fn.startswith("messages"):
            sessions = process_messages(filename, sessions)
        elif fn.startswith("detail"):
            sessions = process_details(filename, sessions)
        else:
            BARF
