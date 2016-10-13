#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import xmlrpc.client
import netrc
from urllib.parse import unquote, quote
import logging
import socket
logger = logging.getLogger(__file__)

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
    authentication = net.authenticators(
      "%s://%s" % (protocol, url,)
    )
    if authentication:
      logger.info("Using authenticated rpc")
      (login, account, password) = authentication
      conn_url = "%(PROTOCOL)s://%(LOGIN)s:%(PASS)s@%(URL)s%(PATH)s/login/xmlrpc" % {"LOGIN" : login,
                                                                                "PASS" : password,
                                                                                "PROTOCOL" : protocol,
                                                                                "PATH" : trac_path,
                                                                                "URL" : url,
      }
      #logger.debug(conn_url)
      server = xmlrpc.client.ServerProxy(conn_url)
    else:
      logger.warn("Using visitor rpc since no authentication provided")
      login = None
      server = \
               xmlrpc.client.ServerProxy(
                 "%(PROTOCOL)s://%(URL)s%(PATH)s/rpc"
                 % {
                    "PROTOCOL" : protocol,
                    "PATH" : trac_path,
                    "URL" : url,
                  }
               )

    try:
      # try anything to make sure the connection is OK
      server.system.listMethods()
    except socket.gaierror as error:
      if error.errno == -2:
        print("Cannot connect to: {}".format(server))

    return (login, server,)
