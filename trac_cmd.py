#!/usr/bin/env python
# -*- coding:utf-8 -*-

import xmlrpclib
import ConfigParser
import cmd
import subprocess
import tempfile
import os
import pprint
import string
import json
import trac_connection
import re
import pickle
from datetime import datetime
from trhaelppyercthon import TPH

class TracCmd(cmd.Cmd):
    def __init__(self, server, login="", url="", template_file="", report_last_time_file=""):
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

        if report_last_time_file:
            self.report_last_time_file = \
                os.path.expanduser(report_last_time_file)

        self.last_recent_change_date = None

    def do_ticket_create(self, line):
        attributes = {
            "type":"Defect",
            "reporter":self.me,
            "status":"new",
        }
        if line:
            attributes.update(json.loads(line))

        ticket_number = self.tph.ticket_create(attributes, True)
        if ticket_number is not None:
            print "Ticket %s created" % (ticket_number)
        else:
            print "Creation aborted"

    def do_ticket_clone(self, line):
        (ticket_number, attributes, ) = self._ticket_attributes_parse_line(line)
        new_ticket_number = self.tph.ticket_clone(ticket_number, attributes,
                                                  True, reporter=self.me)
        if new_ticket_number:
            print "Ticket %s, clone of %s, created" % (new_ticket_number,
                                                       ticket_number)
        else:
            print "Clone ticket not created"

    def do_ticket_son_create(self, line):
        (ticket_number, attributes,) = self._ticket_attributes_parse_line(line)
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
        (ticket_number, attributes,) = self._ticket_attributes_parse_line(line)
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
        assert ticket_number, "argument cannot be empty"
        print self.tph.ticket_sons(ticket_number)

    def do_ticket_parents(self, ticket_number):
        assert ticket_number, "argument cannot be empty"
        print self.tph.ticket_parents(int(ticket_number))

    def do_ticket_accept(self, ticket_number):
        assert ticket_number, "argument cannot be empty"
        if self.tph.ticket_accept(int(ticket_number), self.me):
            print "Ticket %s accepted" % ticket_number
        else:
            print "Abort the acceptation of the ticket %s" % ticket_number

    def do_ticket_remaining_time(self, ticket_numbers):
        assert ticket_numbers, "argument cannot be empty"
        ticket_numbers = ticket_numbers.split(" ")
        self._ticket_remaining_time(ticket_numbers)

    def do_ticket_query_remaining_time(self, query):
        assert query, "argument cannot be empty"
        ticket_numbers = self.tph.server.ticket.query(query)
        self._ticket_remaining_time(ticket_numbers)

    def do_ticket_remaining_time_sum(self, ticket_number):
        assert ticket_number, "argument cannot be empty"
        print self.tph.ticket_remaining_time_sum(ticket_number)

    def do_ticket_recent_changes(self, date_time):
        date = self._parse_date_recent_changes(date_time)
        print("Report for date %s" % date)
        changes = self.tph.ticket_recent_changes(
            date,
            filter=lambda log:not (
                log[3] == "comment" \
                and log[5] == ""
            )
        )
        # recent changes do not show created tickets get the created tickets
        # from that time
        self.last_recent_change_date = datetime.utcnow()
        for change in sorted(changes, key=lambda change:change[1]):
            #self.pp.pprint(change)
            self._dump_change(change)

    def do_ticket_recent_changes_save_date(self, date_time):
        """record the last report date.
        If a date is given as argument, use that date.
        Default to the last report date"""
        assert self.report_last_time_file,\
            "You must indicate a file in the config file"
        if date_time:
            date = self._parse_date(date_time)
        else:
            assert self.last_recent_change_date,\
                "You must give a date or run ticket_recent_changes"
            date = self.last_recent_change_date
        with open(self.report_last_time_file, "w") as fi:
            pickle.dump(date, fi)
        print "Recorded the last time of the report at %s" % date.strftime("%d/%m/%y %H:%M:%S")

    def do_ticket_mine(self, line):
        print "Accepted tickets"
        self.do_ticket_query("owner=%s&status=accepted" % self.me)

    def do_ticket_mine_pending(self, line):
        print "Assigned tickets"
        self.do_ticket_query("owner=%s&status=assigned" % self.me)
        print "New tickets"
        self.do_ticket_query("owner=%s&status=new" % self.me)

    def do_ticket_close(self, ticket):
        if self.tph.ticket_close(int(ticket)):
            print "Closed ticket %s" % (ticket)
        else:
            print "Failed to close ticket"

    def do_ticket_summary(self, ticket):
        print self.tph.ticket_get(int(ticket))[3]["summary"]

    def do_ticket_search(self, query):
        self.pp.pprint(
            self.tph.server.search.performSearch(
                query,
                ["ticket",]
            )
        )

    def do_ticket_edit(self, ticket_numbers):
        ticket_numbers = ticket_numbers.split(" ")
        for ticket_number in ticket_numbers:
            print "Editing ticket %s" % ticket_number
            if self.tph.ticket_edit(int(ticket_number)):
                print "Ticket %s edited" % (ticket_number)
            else:
                print "Edition aborted"

    def do_ticket_edit_batch(self, tickets):
        tickets = [int(ticket) for ticket in tickets.split(" ")]
        self._ticket_edit_batch(tickets)

    def do_ticket_query_edit_batch(self, query):
        tickets = self.tph.server.ticket.query(query)
        self._ticket_edit_batch(tickets)

    def do_ticket_changelog(self, line):
        """Args: ticket number_of_changes
        number_of_changes default to 10
        number_of_changes set to 0 means no limit
        """
        match = re.match(" *([0-9]+)( +([0-9]+))?", line)
        ticket_number = match.group(1)
        lines = match.group(3) or "10"
        changelog = self.tph.ticket_changelog(
            ticket_number,
            filter=lambda log:not (
                log[3] == "comment" \
                and log[5] == ""
            )
        )
        changelog.reverse()
        if lines != "0":
            changelog = changelog[:int(lines)]
        changelog.reverse()
        for change in changelog:
            self._dump_change(change)

    def do_template_edit(self, line):
        if self.tph.template_edit():
            print "Edited template"
        else:
            print "Edition aborted"

    def do_template_save(self, filename):
        if not filename:
            assert self.template_file,\
                "You should provide the template file or set TRAC_CMD_TEMPLATE_FILE"
            filename = self.template_file
        if self.tph.template_save(filename):
            print "Template file saved in %s" % (filename,)
        else:
            print "Template file not saved"

    def do_template_open(self, filename):
        if not filename:
            assert self.template_file,\
                "You should provide the template file or set TRAC_CMD_TEMPLATE_FILE"
            filename = self.template_file
        if self.tph.template_open(filename):
            print "Template file %s loaded" % (filename,)
        else:
            print "Template file not loaded"

    def do_milestone_edit(self, milestone_name):
        if self.tph.milestone_edit(milestone_name):
            print "Milestone %s edited" % milestone_name
        else:
            print "Edition aborted of milestone %s" % milestone_name

    def do_milestone_list(self, list):
        self.pp.pprint(sorted(self.tph.milestone_list()))

    def do_milestone_remaining_time_sum(self, milestone_name):
        print self.tph.milestone_time_sum(milestone_name)

    def do_wiki_search(self, query):
        self.pp.pprint(
            self.tph.server.search.performSearch(
                query,
                ["wiki",]
            )
        )

    def do_list_attachment(self, ticket):
        print self.tph.server.ticket.listAttachments(int(ticket))

    def do_list_components(self, match):
        filter = lambda x:re.search(match, x, re.I)
        for comp in self.tph.list_components(filter):
            print comp

    def do_list_resolution(self, line):
        self.pp.pprint(self.tph.server.ticket.resolution.getAll())

    def do_list_priority(self, line):
        self.pp.pprint(self.tph.server.ticket.priority.getAll())

    def do_list_status(self, line):
        self.pp.pprint(self.tph.server.ticket.status.getAll())

    def do_list_type(self, line):
        self.pp.pprint(self.tph.server.ticket.type.getAll())

    def do_method_list(self, line):
        for method in self.tph.server.system.listMethods():
            print method

    def do_method_help(self, method):
        print self.tph.server.system.methodHelp(method)

    def do_get_actions(self, ticket):
        print self.tph.server.ticket.getActions(int(ticket))

    def do_verbatim(self, line):
        exec("self.pp.pprint(self.tph.server.%s" % line + ")")

    def do_iam(self, line):
        self.me = line

    def do_whoami(self, line):
        print self.me

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

    def do__dump_ticket(self, ticket):
        self.pp.pprint(self.tph.ticket_get(int(ticket)))

    def do__api(self, ticket):
        subprocess.Popen(
            [os.environ['BROWSER'],
             "%(URL)s/login/xmlrpc" % {"URL" : self.url}],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    def _ticket_attributes_parse_line(self, line):
        '''Ex: 72 {"summary":"New ticket"}'''
        content_match = re.match(" *([0-9]+)( +(.+))?", line)
        ticket_number = content_match.group(1)
        attributes = content_match.group(3)
        if attributes:
            attributes = json.loads(attributes)
        else:
            attributes = {}

        return (ticket_number, attributes, )

    def _parse_date_recent_changes(self, date_time):
        if date_time:
            date = self._parse_date(date_time)
        elif self.report_last_time_file \
           and os.path.exists(self.report_last_time_file):
            with open(self.report_last_time_file, "r") as fi:
                date = pickle.load(fi)
        elif self.last_recent_change_date:
            date = self.last_recent_change_date
        else:
            date = datetime(month=1, year=1970, day=1)
        return date

    def _dump_change(self, change):
        date_tuble = change[1].timetuple()
        date = datetime(
            date_tuble.tm_year,
            date_tuble.tm_mon,
            date_tuble.tm_mday,
            date_tuble.tm_hour,
            date_tuble.tm_min,
            date_tuble.tm_sec
        )
        print "  At %s" % (date.strftime("%d/%m/%y %H:%M:%S"),)
        print "%s" % change[2],
        print "Ticket : %s" % change[0],
        if re.search("comment", change[3]):
            print "Added/Edited comment : %s" % change[5].splitlines()[0]
        elif change[3] == "description":
            print "changed the description of the ticket"
        elif change[3] == "created":
            print "created the ticket"
        elif change[3] == "component":
            print "moved the component from %s to %s" % (change[4], change[5],)
        elif change[3] == "summary":
            print "updated summary : %s" % (change[5],)
        elif change[3] == "blocking":
            print "update blocking from %s to %s" % (change[4], change[5],)
        elif change[3] == "status":
            print "changed the status from %s to %s" % (change[4], change[5],)
        elif change[3] == "estimatedhours":
            print "updated estimated hours (%s -> %s)" % (change[4], change[5],)
        elif change[3] == "resolution":
            print "closed the ticket with reason %s" % (change[5],)
        elif change[3] == "owner":
            print "changed owner form %s to %s" % (change[4], change[5],)
        elif change[3] == "keywords":
            print "changed keywords form %s to %s" % (change[4], change[5],)
        elif change[3] == "milestone":
            print "changed milestone form %s to %s" % (change[4], change[5],)
        elif change[3] == "parents":
            print "changed parents form %s to %s" % (change[4], change[5],)
        elif change[3] == "priority":
            print "changed priority form %s to %s" % (change[4], change[5],)
        else:
            self.pp.pprint(change)

    def _parse_date(self, date_time):
        if re.search(date_time, "today"):
            time = datetime.today().replace(
                hour = 0,
                minute = 0,
                second = 0
            )
        elif re.search(date_time, "now"):
            time = datetime.utcnow()
        elif re.search(date_time, "yesterday"):
            time = datetime.today()
            time = time.replace(
                day = time.day - 1,
                hour = 0,
                minute = 0,
                second = 0
            )
        elif date_time.__class__ == str:
            time = datetime.strptime(
                date_time,
                "%d/%m/%y %H:%M:%S"
            )
        else:
            assert False, "Cannot parse %s for a date" % date_time

        return time

    def do_EOF(self, line):
        return True

TracCmd.do_list_milestones = TracCmd.do_milestone_list
TracCmd.do_list_methods = TracCmd.do_method_list
TracCmd.do_help_method = TracCmd.do_method_help

def get_configuration_options():
    config = ConfigParser.ConfigParser()
    config.optionxform = str    # keys not converted into lower case
    config.read(os.environ.get("TRAC_CMDRC",
                               os.path.expanduser("~/.trac_cmdrc.conf")))
    url = config.get("server", "url")
    protocol = config.get("server", "protocol")
    trac_path = config.get("server", "trac_path")
    last_time_file = config.get("report", "last_time_file")
    (login, server) = trac_connection.from_netrc(url, protocol, trac_path)
    return (login, server, protocol, url, trac_path, last_time_file)

def main():
    (login,
     server,
     protocol,
     url,
     trac_path,
     last_time_file) = get_configuration_options()
    TracCmd(server,
            login=login,
            url="%(PROTOCOL)s://%(URL)s%(PATH)s" % {
                "PROTOCOL" : protocol,
                "URL" : url,
                "PATH" : trac_path,
            },
            report_last_time_file=last_time_file
        ).cmdloop()

if __name__ == '__main__':
    main()
