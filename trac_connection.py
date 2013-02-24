#!/usr/bin/env python
# -*- coding:utf-8 -*-

import xmlrpclib
import netrc

def from_netrc(url, protocol, trac_path):
    net = netrc.netrc()
    (login, account, password) = \
                                 net.authenticators(
                                     "%s://%s" % (protocol, url,)
                                 )
    server = \
             xmlrpclib.ServerProxy(
                 "%(PROTOCOL)s://%(LOGIN)s:%(PASS)s@%(URL)s%(PATH)s/login/xmlrpc"
                 % {"LOGIN" : login,
                    "PASS" : password,
                    "PROTOCOL" : protocol,
                    "PATH" : trac_path,
                    "URL" : url,
                }
             )
    return (login, server,)
