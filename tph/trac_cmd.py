#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""Simple command line interface o trac.

It provides high level interactions with the trac to make automatic task be
quick.

TracCmd may be used as is, however, it should be inherited from to add commands
specific to your projects.
"""

import xmlrpclib
import ConfigParser
import cmd
import subprocess
import tempfile
import os
import sys
import pprint
import string
import json
import trac_connection
import re
import pickle
import shlex
import readline
from datetime import datetime
from datetime import timedelta
from trhaelppyercthon import TPH
from attributes import TPHAttributes
from edit import edit
import logging
logging.basicConfig(level=logging.DEBUG)

class TracCmd(cmd.Cmd, object):
    def __init__(self, server, login="", url="", template_file="", report_last_time_file=""):
        """Initializes the TracCmd object.

server, the xml rpc server to use
login, the login name, available as self.me in the commands
url, the url of the server, available is self.url in the commans
template_file, the location of the default template file to use, defaults to the
        environment variable TRAC_CMD_TEMPLATE_FILE and fallback to ""
report_last_time_file, the location of a file storing the last time the ticket
        report has been seen, see the documentation of the ticket_recent_changes
        command for more information.
"""
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
        """Create a new ticket, interpreting the remaining of the line as a
python dictionary containing default attributes."""
        attributes = {
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

    def do_ticket_subscribe_dependencies(self, line):
        content = re.split(" +", line)
        ticket_number = content[0]
        if len(content) == 1:
            persons = [self.me,]
        else:
            persons = content[1:]
        comment = "Added %s in the cc list to trac %s availability for work" % (
            ", ".join(persons),
            ticket_number
        )
        comment = self.tph.edit_comment(comment)
        if not comment:
            print "Subscription aborted"
            return
        blockings = self.tph.ticket_subscribe_dependencies(ticket_number, persons, comment, True)
        print "Added %s into the cc field of tickets %s" % (persons, blockings)

    def do_ticket_clone(self, line):
        """Clone a ticket.

The first argument of the line is the ticket number to clone, the rest is
        interpreted as a python dictionary containing default attributes.
        """
        (ticket_number, attributes, ) = self._ticket_attributes_parse_line(line)
        new_ticket_number = self.tph.ticket_clone(ticket_number, attributes,
                                                  True, reporter=self.me)
        if new_ticket_number:
            print "Ticket %s, clone of %s, created" % (new_ticket_number,
                                                       ticket_number)
        else:
            print "Clone ticket not created"

    def do_ticket_son_create(self, line):
        """Create a son ticket.

The first argument of the line is the ticket number that will be the parent, the
        rest is interpreted as a python dictionary containing default
        attributes.
        """
        (ticket_number, attributes,) = self._ticket_attributes_parse_line(line)
        new_ticket_number = self.tph.ticket_son_create(ticket_number,
                                                       self.me,
                                                       attributes,
                                                       True)
        if new_ticket_number:
            print "Ticket %s, son of %s, created" % (new_ticket_number,
                                                     ticket_number)
        else:
            print "Creation aborted"

    def do_ticket_sibling_create(self, line):
        """Create a sibling of a ticket.

The first argument of the line is the ticket number to clone, the rest is
        interpreted as a python dictionary containing default attributes.
        """
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
        """Perform a ticket query and return the list of matching tickets. The
        query may be for instance "owner=owner&status=accepted"."""
        assert line, "argument cannot be empty"
        print self.tph.server.ticket.query(line)

    def complete_ticket_query(self, text, line, begidx, endidx):
        if re.match("^.+=[^&= ]*$", line):
            # complete on a value
            # find the key
            group = re.match('^.+[ "&]([^ "&]+)=%s$' % text, line)
            key = group.group(1)
            values = [value for value in self.tph.ticket_field_values(key)
                      if value.startswith(text)
            ]
            return values
        else:
            # complete on a key
            # find the key
            group = re.match("^(.+&)?([^&]*)$", text)
            prefix = group.group(1) or ""
            key = group.group(2)
            keys = [prefix + field for field in self.tph.attrs.fields if
                    field.startswith(key)]
            if len(keys) == 1:
                return [keys[0] + "=", ]
            else:
                return keys

    def do_ticket_sons(self, ticket_number):
        """Return the list of sons of ticket_number."""
        assert ticket_number, "argument cannot be empty"
        print self.tph.ticket_sons(ticket_number)

    def do_ticket_sons_recursive(self, ticket_number):
        """Return the list of sons of ticket_number and their sons and the sons
        of their sons and the..."""
        assert ticket_number, "argument cannot be empty"
        self._ticket_sons_recursive(ticket_number, "")

    def do_ticket_parents(self, ticket_number):
        """Returns the list of parents of ticket_number."""
        assert ticket_number, "argument cannot be empty"
        print self.tph.ticket_parents(int(ticket_number))

    def do_ticket_accept(self, ticket_number):
        """Accept ticket_number, that means change the owner to self.me and the
        status to accepted."""
        assert ticket_number, "argument cannot be empty"
        if self.tph.ticket_accept(int(ticket_number), self.me):
            print "Ticket %s accepted" % ticket_number
        else:
            print "Abort the acceptation of the ticket %s" % ticket_number

    def do_ticket_remaining_time(self, ticket_numbers):
        """Display the sum of the remaining times of ticket_numbers."""
        assert ticket_numbers, "argument cannot be empty"
        ticket_numbers = ticket_numbers.split(" ")
        self._ticket_remaining_time(ticket_numbers)

    def do_ticket_remaining_time_sum(self, ticket_numbers):
        """Display the sum of the recursive remaining times of ticket_numbers."""
        assert ticket_numbers, "argument cannot be empty"
        ticket_numbers = ticket_numbers.split(" ")
        self._ticket_remaining_time(ticket_numbers, True)

    def do_ticket_query_remaining_time(self, query):
        """Displays the sum of the remaining times of the tickets matching the
        query."""
        assert query, "argument cannot be empty"
        ticket_numbers = self.tph.server.ticket.query(query)
        self._ticket_remaining_time(ticket_numbers)

    def do_ticket_recent_changes(self, date_time):
        """Dump the recent changes of tickets since date_time. If date_time is
        not given, pickel loads it from self.report_last_time_file."""
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
        self.last_recent_change_date = datetime.today()
        for change in sorted(changes, key=lambda change:change[1]):
            #self.pp.pprint(change)
            self._dump_change(change)

    def do_ticket_recent_changes_save_date(self, date_time):
        """Record the last report date.
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
        """Display all the tickets whose status is accepted and owner is
        self.me."""
        print "Accepted tickets"
        self.do_ticket_query("owner=%s&status=accepted" % self.me)

    def do_ticket_mine_pending(self, line):
        """Display all the tickets whose status is either assigned or new and owner is
        self.me.

        """
        print "Assigned tickets"
        self.do_ticket_query("owner=%s&status=assigned" % self.me)
        print "New tickets"
        self.do_ticket_query("owner=%s&status=new" % self.me)

    def do_ticket_close(self, ticket):
        """Close the ticket ticket."""
        if self.tph.ticket_close(int(ticket)):
            print "Closed ticket %s" % (ticket)
        else:
            print "Failed to close ticket"

    def do_ticket_summary(self, ticket):
        """Dumps the summary of the ticket."""
        print self.tph.ticket_get(int(ticket))[3]["summary"]

    def do_ticket_description(self, ticket):
        """Dumps the description of ticket."""
        print self.tph.ticket_get(int(ticket))[3]["description"]

    def do_ticket_search(self, query):
        """Dumps the result of the search of query in tickets."""
        self.pp.pprint(
            self.tph.server.search.performSearch(
                query,
                ["ticket",]
            )
        )

    def do_ticket_edit(self, ticket_numbers):
        """Edit the tickets whose ids are in ticket_numbers."""
        ticket_numbers = ticket_numbers.split(" ")
        self._ticket_edit(ticket_numbers)

    def do_ticket_edit_batch(self, tickets):
        """Batch edit the tickets."""
        tickets = self._ticket_list_parse(tickets)
        self._ticket_edit_batch(tickets)

    def do_ticket_query_edit(self, query):
        """Edit the tickets matching query."""
        tickets = self.tph.server.ticket.query(query)
        self._ticket_edit(tickets)

    def do_ticket_query_print(self, line):
        """Print the field of the tickets matching query.
        The first argument is the query, the second argument is the attribute to print.
        """
        [query, field] = shlex.split(line)
        assert field, "Field must be given"
        assert query, "Query must be given"
        tickets = self.tph.server.ticket.query(query)
        for ticket in tickets:
            print ticket, self.tph.ticket_get(ticket)[3][field]

    def do_ticket_print(self, query):
        """Print the field of the tickets.
        The first arguments are the list of tickets, the last argument is the attribute to print.
        """
        items = re.split(" +", query)
        assert len(items) > 1
        tickets = items[0:-1]
        field = items[-1]
        for ticket in tickets:
            print ticket, self.tph.ticket_get(ticket)[3][field]

    def do_ticket_query_edit_batch(self, query):
        """Batch edit all the tickets matching query."""
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

    def do_ticket_query_time_sum(self, query):
        """Displays the sum of the remaining time of all tickets matching query."""
        print self.tph.ticket_query_time_sum(query)

    def do_ticket_attach_list(self, ticket):
        """Display all the attachments of ticket."""
        print self.tph.ticket_attachment_list(ticket)

    def do_ticket_attach_put(self, ticket_attachs):
        """Add an attachment to a ticket.
The first argument is the ticket, the remaining arguments are the files to attach.
"""
        args = re.split(" +", ticket_attachs)
        ticket = args[0]
        assert re.search("^[0-9]+$", ticket)
        attach_files = args[1:]
        assert attach_files
        files = {}
        for fil in attach_files:
            desc = edit("""%s

Description""" % fil)
            if not desc:
                print "Attachment put aborted"
                return
            match = re.search("^[^\n]+\n\n(.+)$", desc)
            desc = match.group(1)
            files[fil] = desc
        print self.tph.ticket_attachment_put(
            ticket,
            files
        )
        print "Files attached to the ticket"

    def do_ticket_split(self, ticket_n_number):
        """Spit ticket in several subtickets.

The first argument is the ticket to split, the second one is the number of
        subtickets. The created tickets are subtickets of the initial one."""
        args = re.split(" +", ticket_n_number)
        ticket = args[0]
        number = args[1]
        assert ticket and re.search("^[0-9]+$", ticket)
        assert number and re.search("^[0-9]+$", number)
        tickets = self.tph.ticket_split(int(ticket), int(number), self.me, use_editor=True)
        if tickets != []:
            print "Ticket %s split into %s" % (ticket, tickets)
        else:
            print "Command aborted"

    def do_template_edit(self, line):
        """Edit the ticket template."""
        if self.tph.template_edit():
            print "Edited template"
        else:
            print "Edition aborted"

    def do_template_save(self, filename):
        """Save the ticket template of the location provided by
        filename."""
        if not filename:
            assert self.template_file,\
                "You should provide the template file or set TRAC_CMD_TEMPLATE_FILE"
            filename = self.template_file
        if self.tph.template_save(filename):
            print "Template file saved in %s" % (filename,)
        else:
            print "Template file not saved"

    def do_template_open(self, filename):
        """Loads the template file from filename."""
        if not filename:
            assert self.template_file,\
                "You should provide the template file or set TRAC_CMD_TEMPLATE_FILE"
            filename = self.template_file
        if self.tph.template_open(filename):
            print "Template file %s loaded" % (filename,)
        else:
            print "Template file not loaded"

    def do_milestone_edit(self, milestone_name):
        """Edit the content of the milestone."""
        if self.tph.milestone_edit(milestone_name):
            print "Milestone %s edited" % milestone_name
        else:
            print "Edition aborted of milestone %s" % milestone_name

    def do_milestone_list(self, match):
        """List the milestones."""
        filter = lambda x:re.search(match, x, re.I)
        for milestone in self.tph.milestone_list(filter):
            print milestone

    def do_milestone_remaining_time_sum(self, milestone_name):
        """Display the remaining time of the milestone_name."""
        print self.tph.milestone_time_sum(milestone_name)

    def do_milestone_stuck_p(self, milestone_name):
        """The milestone is stuck if one of its tickets is blocked by a tickets
not closed or not into the milestone"""
        ticket_numbers = self.tph.server.ticket.query("milestone=%s&blockedby!=" % milestone_name)
        # for each ticket, find out if its blockers are scheduled
        for ticket_number in ticket_numbers:
            ticket = self.tph.ticket_get(int(ticket_number))
            blocking_ticket_numbers = re.split("[ ,]+", ticket[3]["blockedby"])
            for blocking_ticket_number in blocking_ticket_numbers:
                blocking_ticket = self.tph.ticket_get(int(blocking_ticket_number))
                if blocking_ticket[3]["status"] != "closed" \
                   and blocking_ticket[3]["milestone"] != milestone_name:
                    print "%s is blocked by %s not in current milestone" % (
                        ticket_number, blocking_ticket_number
                    )

    def do_wiki_search(self, query):
        """Print the result of the search of query into the wiki"""
        self.pp.pprint(
            self.tph.server.search.performSearch(
                query,
                ["wiki",]
            )
        )

    def do_list_attachment(self, ticket):
        """List the attachments of ticket"""
        print self.tph.server.ticket.listAttachments(int(ticket))

    def do_list_components(self, match):
        """Prints the list of components."""
        filter = lambda x:re.search(match, x, re.I)
        for comp in self.tph.component_list(filter):
            print comp

    def do_list_resolution(self, line):
        """Print the list of the resolutions."""
        self.pp.pprint(self.tph.server.ticket.resolution.getAll())

    def do_list_priority(self, line):
        """Print the list of the priority."""
        self.pp.pprint(self.tph.server.ticket.priority.getAll())

    def do_list_status(self, line):
        """Print the list of the status."""
        self.pp.pprint(self.tph.server.ticket.status.getAll())

    def do_list_type(self, line):
        """Print the list of the type."""
        self.pp.pprint(self.tph.server.ticket.type.getAll())

    def do_wiki_attach_list(self, page):
        """Print the list of files attached to the wiki page."""
        for attachment in self.tph.wiki_attachment_list(page):
            print attachment

    def do_wiki_attach_put(self, page_attachs):
        """Attach some files to the wiki page.

The first argument is the wiki page, the remaining ones are the files to attach.

Existing attachments with the same name will be overwritten."""
        args = re.split(" +", page_attachs)
        page = args[0]
        attach_files = args[1:]
        assert attach_files
        files = {}

        print self.tph.wiki_attachment_put(
            page,
            attach_files
        )
        print "Files attached to the page"

    def do_wiki_attach_delete(self, page_attachs):
        """Delete some attachments from the wiki. The arguments are the addresses
        of the attachments to delete."""
        attachments = re.split(" +", page_attachs)
        assert attachments

        for attachment in attachments:
            self.tph.server.wiki.deleteAttachment(
                attachment
            )
            print "File %s deleted" % attachment

    def do_wiki_attach_get(self, page_attachs):
        """Get some attachments from the wiki into the current directory. The arguments are the addresses
        of the attachments to get (in case of conflict, the last file overrides
        the previous ones)."""
        attachments = re.split(" +", page_attachs)
        assert attachments
        self._wiki_attach_get(attachments)

    def do_wiki_attach_get_from_wiki_page_name(self, wiki_page_name):
        """Get all the attachment of a wiki page into the current directory."""
        attachments = self.tph.wiki_attachment_list(wiki_page_name)
        self._wiki_attach_get(attachments)

    def do_method_list(self, line):
        """List the XML RPC available methods. Useful for debugging."""
        for method in self.tph.server.system.listMethods():
            print method

    def do_method_help(self, method):
        """Prints the help of an XML RPC method. Useful for debugging."""
        print self.tph.server.system.methodHelp(method)

    def do_get_actions(self, ticket):
        """List the availables actions to perform on a ticket. Useful for debugging."""
        print self.tph.server.ticket.getActions(int(ticket))

    def do_verbatim(self, line):
        """Call the XML RPT method like if directly called on the server (in
        python syntax). Useful for debugging."""
        exec("self.pp.pprint(self.tph.server.%s" % line + ")")

    def do_ticket_field_values(self, field):
        """Return the possible values for field"""
        print self.tph.ticket_field_values(field)

    def do_iam(self, line):
        """Change who is self.me"""
        self.me = line

    def do_whoami(self, line):
        """Prints the content of self.me"""
        print self.me

    def do_ticket_web(self, tickets):
        """Open the tickets in the web browser."""
        tickets = re.split(" +", tickets)
        for ticket in tickets:
            url="%(URL)s/ticket/%(TICKET)s" % {
                "URL" : self.url,
                "TICKET" : ticket,
            }
            self._open_in_browser(url)

    def do_ticket_query_web(self, query):
        """Open all the tickets matching query in the web browser."""
        tickets = self.tph.server.ticket.query(query)
        for ticket in tickets:
            url="%(URL)s/ticket/%(TICKET)s" % {
                "URL" : self.url,
                "TICKET" : ticket,
            }
            self._open_in_browser(url)

    def do_wiki_web(self, page):
        """Open the wiki page with the web browser."""
        url="%(URL)s/wiki/%(WIKI)s" % {
            "URL" : self.url,
            "WIKI" : page,
        }
        self._open_in_browser(url)

    def do__dump_ticket(self, ticket):
        """Dump the content of the ticket. Used for debugging."""
        self.pp.pprint(self.tph.ticket_get(int(ticket)))

    def do__interpreter(self, line):
        """Launch an interpreter."""
        import readline, rlcompleter
        readline.parse_and_bind("tab: complete")
        import code
        code.interact(local=locals())

    def do__api(self, ticket):
        """Open the API page with the browser"""
        subprocess.Popen(
            [os.environ['BROWSER'],
             "%(URL)s/login/xmlrpc" % {"URL" : self.url}],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    def _ticket_remaining_time(self, ticket_numbers, sum=False):
        """Prints the remaining time of ticket_numbers. If sum is True, then the
        time of a ticket is the sum of its time and the time of all its children."""
        total = 0
        for ticket_number in ticket_numbers:
            if sum:
                value = self.tph.ticket_remaining_time_sum(ticket_number)
            else:
                value = self.tph.ticket_remaining_time(ticket_number)
            total += value
            print ticket_number,value
        if len(ticket_numbers) > 1:
            print "---"
            print "Total :",total

    def _ticket_edit(self, ticket_numbers):
        """Open tickets for edition."""
        total = len(ticket_numbers)
        print "%s tickets to edit" % total
        for ticket_number in ticket_numbers:
            print "Editing ticket %s" % ticket_number
            if self.tph.ticket_edit(int(ticket_number)):
                total -= 1
                print "Ticket %s edited, %s left" % (ticket_number, total)
            else:
                print "Edition aborted"

    def _ticket_edit_batch(self, ticket_numbers):
        """Open tickets for batch edition."""
        attributes = {
            field : ""
            for field in self.tph.attrs.fields
        }
        attributes = self.tph.attrs.edit(attributes, prefix="merge_attributes_")
        if not attributes:
            print "Abort edition"
            return
        comment = edit("Comment")
        if not comment:
            print "Aborting due to empty comment"
            return
        for ticket_number in ticket_numbers:
            print "Editing ticket %s" % ticket_number
            print "Merging attributes"
            ticket = self.tph.ticket_get(ticket_number)
            new_attributes = self.tph.attrs.merge(ticket[3], attributes, True)
            # handle the special case where nothing has changed
            if new_attributes == ticket[3]:
                print "Nothing to do for ticket %s" % ticket_number
            else:
                if self.tph.server.ticket.update(
                        ticket_number,
                        comment,
                        new_attributes,
                        True
                ):
                    print "Ticket %s edited" % (ticket_number)
                else:
                    print "Failed to edit ticket %s" % (ticket_number)

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

    def _ticket_list_parse(self, line):
        """For a line representing a list of tickets, return a list of tickets numbers."""
        return [int(ticket.replace("#", ""))
                for ticket in re.split("#? +", line)]

    def _parse_date_recent_changes(self, date_time):
        """Parse the line given by the user as recent change date and return a date."""
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
        """Dump a change returned by the ticket.changeLog XML RPC method."""
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
            if change[5] == "":
                print "reopened the ticket, removing the reason %s" % (change[4],)
            else:
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
        elif change[3] == "score":
            print "changed score form %s to %s" % (change[4], change[5],)
        else:
            self.pp.pprint(change)

    def _ticket_sons_recursive(self, ticket_number, indent):
        """Prints a hierarchy of tickets."""
        print indent + str(ticket_number)
        for son in self.tph.ticket_sons(ticket_number):
            self._ticket_sons_recursive(son, indent + "  ")

    def _open_in_browser(self, url):
        """Open the url with the web browser."""
        subprocess.Popen(
            [os.environ['BROWSER'],
             url
         ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    def _parse_date(self, date_time):
        """Parse a date and return a time object."""
        if re.search(date_time, "today"):
            time = datetime.today().replace(
                hour = 0,
                minute = 0,
                second = 0
            )
        elif re.search(date_time, "now"):
            time = datetime.utcnow()
        elif re.search(date_time, "yesterday"):
            time = datetime.today().replace(
                hour = 0,
                minute = 0,
                second = 0
            ) + timedelta(-1)
        elif date_time.__class__ == str:
            time = datetime.strptime(
                date_time,
                "%d/%m/%y %H:%M:%S"
            )
        else:
            assert False, "Cannot parse %s for a date" % date_time

        return time

    def _wiki_attach_get(self, attachments):
        for attachment in attachments:
            attachment_binary = self.tph.server.wiki.getAttachment(
                attachment
            )
            attachment_name = os.path.basename(attachment)
            dest_file_name = os.path.join(os.getcwd(), attachment_name)
            open(attachment_name, "w").write(attachment_binary.data)
            print "File %s got and written into %s" % (attachment,
                                                       dest_file_name)

    def do_EOF(self, line):
        """EOF command quits the application"""
        return True

# those are shortcuts to make the usage of the command line easier
TracCmd.do_list_milestones = TracCmd.do_milestone_list
TracCmd.do_list_methods = TracCmd.do_method_list
TracCmd.do_help_method = TracCmd.do_method_help
TracCmd.complete_ticket_query_print = TracCmd.complete_ticket_query


def get_configuration_options():
    """Get the configuration from a configuration file stored in the filesystem.

try the environment variable TRAC_CMD, if it does not exist, fallback to
    ~/.trac_cmdrc.conf.

The format of the configuration file is expected to be:
[server]
url=...
trac_path=...
protocol=...
[report]
last_time_file=...

See the trac_connection library for more information about the server part and
    the documentation of TracCmd for the documentation of last_time_file.
"""
    configuration_file = os.environ.get("TRAC_CMDRC",
                   os.path.expanduser("~/.trac_cmdrc.conf"))
    if not os.path.exists(configuration_file):
      logging.error("Could not find configuration file %s" % configuration_file)
      sys.exit(1)
    config = ConfigParser.ConfigParser()
    config.optionxform = str    # keys not converted into lower case
    config.read(configuration_file)
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

# Local Variables:
# python-indent: 4
# End:
