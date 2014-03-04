#!/usr/bin/env python
# -*- coding:utf-8 -*-

import xmlrpclib
import netrc
from urllib import unquote, quote

def from_netrc(url, protocol, trac_path):
    """Retrieve connection information from netrc.

url is the url of the server to be connected to, without the protocol part.
protocol is the protocol to use.
trac_path is the path to trac.

For instance, if connecting to https://somesite/trac/, then url, protocol,
    trac_path should be somesite, https and trac. the associated machine entry
    in netrc is expected to be https://somesite
    """
    net = netrc.netrc()
    (login, account, password) = \
                                 net.authenticators(
                                     "%s://%s" % (protocol, url,)
                                 )
    server = \
             xmlrpclib.ServerProxy(
                 "%(PROTOCOL)s://%(LOGIN)s:%(PASS)s@%(URL)s%(PATH)s/login/xmlrpc"
                 % {"LOGIN" : quote(login),
                    "PASS" : quote(password),
                    "PROTOCOL" : protocol,
                    "PATH" : trac_path,
                    "URL" : url,
                }
             )
    return (login, server,)
