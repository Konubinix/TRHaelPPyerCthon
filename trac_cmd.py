#!/usr/bin/env python
# -*- coding:utf-8 -*-

import xmlrpclib
import netrc                    # to access to credentials
import ConfigParser
import cmd
import subprocess
import tempfile
import os
import pprint
import string
import json
import re
from trhaelppyercthon import TPH

class TracCmd(cmd.Cmd):
    def __init__(self, server, login="", url="", template_file=""):
        cmd.Cmd.__init__(self)
        self.tph = TPH(server)
        self.me = login
        self.pp = pprint.PrettyPrinter(indent=4)
        self.url = url
        self.template_file = template_file \
                             or \
                             os.environ.get("TRAC_CMD_TEMPLATE_FILE", "")
        if self.template_file \
           and \
           os.path.exists(self.template_file):
            self.tph.template_open(self.template_file)

    def do_method_list(self, line):
        for method in self.tph.server.system.listMethods():
            print method

    def do_method_help(self, method):
        print self.tph.server.system.methodHelp(method)

    def ticket_attributes_parse_line(self, line):
        '''Ex: 72 {"summary":"New ticket"}'''
        content_match = re.match(" *([0-9]+)( +(.+))?", line)
        ticket_number = content_match.group(1)
        attributes = content_match.group(3)
        if attributes:
            attributes = json.loads(attributes)
        else:
            attributes = {}

        return (ticket_number, attributes, )

    def do_ticket_create(self, line):
        attributes = {}
        if line:
            attributes.update(json.loads(line))

        ticket_number = self.tph.ticket_create(attributes, True)
        if ticket_number is not None:
            print "Ticket %s created" % (ticket_number)
        else:
            print "Creation aborted"

    def do_ticket_clone(self, line):
        (ticket_number, attributes, ) = self.ticket_attributes_parse_line(line)
        new_ticket_number = self.tph.ticket_clone(ticket_number, attributes,
                                                  True, reporter=self.me)
        if new_ticket_number:
            print "Ticket %s, clone of %s, created" % (new_ticket_number,
                                                       ticket_number)
        else:
            print "Clone ticket not created"

    def do_ticket_son_create(self, line):
        (ticket_number, attributes,) = self.ticket_attributes_parse_line(line)
        new_ticket_number = self.tph.ticket_son_create(ticket_number,
                                                       attributes,
                                                       True,
                                                       reporter=self.me)
        if new_ticket_number:
            print "Ticket %s, son of %s, created" % (new_ticket_number,
                                                     ticket_number)
        else:
            print "Creation aborted"

    def do_ticket_sibling_create(self, line):
        (ticket_number, attributes,) = self.ticket_attributes_parse_line(line)
        new_ticket_number = self.tph.ticket_sibling_create(
            ticket_number,
            attributes,
            True,
            reporter=self.me
        )
        if new_ticket_number:
            print "Ticket %s, sibling of %s, created" % (new_ticket_number,
                                                         ticket_number)
        else:
            print "Creation aborted"

    def do_ticket_query(self, line):
        """owner=owner&status=accepted"""
        assert line, "argument cannot be empty"
        print self.tph.server.ticket.query(line)

    def do_ticket_sons(self, ticket_number):
        print self.tph.server.ticket.query("parents=~%s" % (ticket_number))

    def do_ticket_accept(self, ticket_number):
        assert ticket_number, "argument cannot be empty"
        if self.tph.ticket_accept(int(ticket_number), self.me):
            print "Ticket %s accepted" % ticket_number
        else:
            print "Abort the acceptation of the ticket %s" % ticket_number

    def do_ticket_remaining_time(self, ticket_number):
        assert ticket_number, "argument cannot be empty"
        print self.tph.ticket_remaining_time(ticket_number)

    def do_ticket_remaining_time_sum(self, ticket_number):
        assert ticket_number, "argument cannot be empty"
        print self.tph.ticket_remaining_time_sum(ticket_number)

    def do_template_edit(self, line):
        if self.tph.template_edit():
            print "Edited template"
        else:
            print "Edition aborted"

    def do_template_save(self, filename):
        if self.tph.template_save(filename):
            print "Template file saved"
        else:
            print "Template file not saved"

    def do_template_open(self, filename):
        if self.tph.template_open(filename):
            print "Template file loaded"
        else:
            print "Template file not loaded"

    def do_iam(self, line):
        self.me = line

    def do_whoami(self, line):
        print self.me

    def do_ticket_mine(self, line):
        self.do_ticket_query("owner=%s&status=accepted" % self.me)

    def do_ticket_mine_pending(self, line):
        self.do_ticket_query("owner=%s&status=assigned" % self.me)

    def do_ticket_close(self, ticket):
        if self.tph.ticket_close(int(ticket)):
            print "Closed ticket %s" % (ticket)
        else:
            print "Failed to close ticket"

    def do_list_attachment(self, ticket):
        print self.tph.server.ticket.listAttachments(int(ticket))

    def do_list_components(self, filter):
        self.pp.pprint(
            self.tph.list_components(filter)
        )

    def do_list_resolution(self, line):
        self.pp.pprint(self.tph.server.ticket.resolution.getAll())

    def do_list_priority(self, line):
        self.pp.pprint(self.tph.server.ticket.priority.getAll())

    def do_list_status(self, line):
        self.pp.pprint(self.tph.server.ticket.status.getAll())

    def do_list_type(self, line):
        self.pp.pprint(self.tph.server.ticket.type.getAll())

    def do_get_actions(self, ticket):
        print self.tph.server.ticket.getActions(int(ticket))

    def do_verbatim(self, line):
        exec("print self.tph.server.%s" % line)

    def do_ticket_edit(self, ticket_number):
        if self.tph.ticket_edit(int(ticket_number)):
            print "Ticket %s edited" % (ticket_number)
        else:
            print "Edition aborted"

    def do_ticket_changelog(self, line):
        """Args: ticket number_of_changes
        number_of_changes default to 10
        number_of_changes set to 0 means no limit
        """
        match = re.match(" *([0-9]+)( +([0-9]+))?", line)
        ticket_number = match.group(1)
        lines = match.group(3) or "10"
        changelog = self.tph.server.ticket.changeLog(ticket_number)
        changelog.reverse()
        if lines != "0":
            changelog = changelog[:int(lines)]
        self.pp.pprint(changelog)

    def do_web(self, ticket):
        url="%(URL)s/ticket/%(TICKET)s" % {
            "URL" : self.url,
            "TICKET" : ticket,
        }
        subprocess.Popen(
            [os.environ['BROWSER'],
             url
         ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    def do_change_parents(self, ticket):
        self.change_part(ticket, 'parents')

    def do__dump_ticket(self, ticket):
        self.pp.pprint(self.tph.ticket_get(int(ticket)))

    def do_ticket_search(self, query):
        self.pp.pprint(
            self.tph.server.search.performSearch(
                query,
                ["ticket",]
            )
        )

    def do_wiki_search(self, query):
        self.pp.pprint(
            self.tph.server.search.performSearch(
                query,
                ["wiki",]
            )
        )

    def do__api(self, ticket):
        subprocess.Popen(
            [os.environ['BROWSER'],
             "%(URL)s/login/xmlrpc" % {"URL" : self.url}],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    def do_milestone_edit(self, milestone_name):
        if self.tph.milestone_edit(milestone_name):
            print "Milestone %s edited" % milestone_name
        else:
            print "Edition aborted of milestone %s" % milestone_name

    def do_milestone_list(self, list):
        self.pp.pprint(sorted(self.tph.milestone_list()))

    def do_EOF(self, line):
        return True

TracCmd.do_list_milestones = TracCmd.do_milestone_list
TracCmd.do_list_methods = TracCmd.do_method_list

def main():
    config = ConfigParser.ConfigParser()
    config.optionxform = str    # keys not converted into lower case
    config.read(os.environ.get("TRAC_CMDRC",
                               os.path.expanduser("~/.trac_cmdrc.conf")))
    url = config.get("server", "url")
    protocol = config.get("server", "protocol")
    trac_path = config.get("server", "trac_path")
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
    TracCmd(server,
            login=login,
            url="%(PROTOCOL)s://%(URL)s%(PATH)s" % {
                "PROTOCOL" : protocol,
                "URL" : url,
                "PATH" : trac_path,
            }
        ).cmdloop()

if __name__ == '__main__':
    main()
