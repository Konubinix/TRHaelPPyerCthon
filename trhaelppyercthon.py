#!/usr/bin/env python
# -*- coding:utf-8 -*-

import netrc
import tempfile
import subprocess
import datetime
import os
import re
import xmlrpclib

from attributes import TPHAttributes
from edit import edit

class TPH(object):
    def __init__(self, server):
        self.server = server
        self.attrs = TPHAttributes(
            (
                'summary',
                'component',
                'estimatedhours',
                'keywords',
                'cc',
                'milestone',
                'owner',
                'parents',
                'blockedby',
                'blocking',
                'priority',
                'reporter',
                'resolution',
                'startdate',
                'status',
                'type',
            )
        )
        self.template_attributes = {}

    def edit_comment(self, comment="", info="", prefix=""):
        info_string = "\n".join([
            "# " + line for line in info.splitlines()
        ])
        info_string = "\n# lines beginning with # are avoided\n" + info_string
        comment = edit(comment + info_string, prefix=prefix)
        if not comment:
            return None
        # remove the lines beginning with #
        new_comment_lines = [
            line for line in comment.splitlines()
            if not re.search("^#", line)
        ]
        return "\n".join(new_comment_lines)

    def ticket_create(self, p_attributes, use_editor=False):
        attributes = self.template_attributes.copy()
        attributes.update(p_attributes)
        summary = attributes.get("summary","Summary")
        description = attributes.get("description","Description\n")
        if use_editor:
            attributes["summary"] = summary
            attributes["description"] = description
            attributes = self.attrs.edit(attributes)
            if attributes == None:
                return None

        return self.server.ticket.create(
            summary,
            description,
            attributes)

    def ticket_clone(self, ticket_number, attributes, use_editor=False, reporter=""):
        # get the ticket to clone
        ticket = self.ticket_get(ticket_number)
        ticket_attributes = ticket[3]
        # remove what is not relevant in the ticket
        for key in ("changetime", "_ts", "time",):
            del ticket_attributes[key]
            # addition of the overriding attributes
            ticket_attributes.update(attributes)
            # I am the new reporter of the ticket
            ticket_attributes["reporter"] = reporter
            #self.pp.pprint(ticket_attributes)

        return self.ticket_create(ticket_attributes, use_editor)

    def ticket_son_create(self, ticket_number, attributes, use_editor=False, reporter=""):
        # get the ticket to clone
        ticket = self.ticket_get(ticket_number)
        ticket_old_attributes = ticket[3]
        # get only the relevant info to copy from the parent ticket
        ticket_attributes = {
            "cc" : ticket_old_attributes["cc"],
            "component" : ticket_old_attributes["component"],
            "estimatedhours" : ticket_old_attributes["estimatedhours"],
            "keywords" : "",    # new set of keywords
            "milestone" : ticket_old_attributes["milestone"],
            "owner" : ticket_old_attributes["owner"],
            "parents" : "#" + str(ticket[0]),
            "priority" : ticket_old_attributes["priority"],
            "reporter" : reporter,
            "summary" : ticket_old_attributes["summary"] + " - Sub ticket",
            "status" : "new",
            "description" : ticket_old_attributes["description"],
            'type': 'Defect',
        }
        ticket_attributes.update(attributes)
        return self.ticket_create(ticket_attributes, use_editor)

    def ticket_batch_set(self, id_list, attributes):
        for id in id_list:
            self.server.ticket.update(int(id),
                                      "",
                                      attributes
                                  )

    def ticket_sibling_create(self, ticket_number, attributes, use_editor=False, reporter=""):
        # get the ticket to clone
        ticket = self.ticket_get(ticket_number)
        ticket_old_attributes = ticket[3]
        # get only the relevant info to copy from the sibling ticket
        ticket_attributes = {
            "cc" : ticket_old_attributes["cc"],
            "component" : ticket_old_attributes["component"],
            "estimatedhours" : ticket_old_attributes["estimatedhours"],
            "keywords" : ticket_old_attributes["keywords"],
            "milestone" : ticket_old_attributes["milestone"],
            "owner" : ticket_old_attributes["owner"],
            "parents" : ticket_old_attributes["parents"],
            "priority" : ticket_old_attributes["priority"],
            "reporter" : reporter,
            "summary" : ticket_old_attributes["summary"] + " - Sibling",
            "status" : "new",
            "description" : ticket_old_attributes["description"],
            'type': ticket_old_attributes["type"],
        }
        # update the attributes with the ones provided in argument
        ticket_attributes.update(attributes)
        return self.ticket_create(ticket_attributes, use_editor)

    def ticket_get(self, ticket):
        return self.server.ticket.get(ticket)

    def ticket_close(self, ticket):
        content = edit("fixed\n\nComment")
        if content == "":
            return False
        content_split = content.splitlines()
        resolution = content_split[0]
        comment = "\n".join(content_split[2:])
        self.server.ticket.update(ticket,
                                  comment,
                                  {
                                      'action':'resolve',
                                      'action_resolve_resolve_resolution': resolution,
                                  }
                              )
        return True

    def ticket_edit(self, ticket_number):
        ticket = self.ticket_get(ticket_number)
        attributes = ticket[3]
        attributes = self.attrs.edit(attributes, str(ticket_number))
        if attributes:
            attributes_string = self.attrs.dump(attributes)
            comment = self.edit_comment(info=attributes_string, prefix=str(ticket_number))
            if comment is None:
                return False
            self.server.ticket.update(
                ticket[0],
                comment,
                attributes
            )
            return True
        else:
            return False

    def ticket_accept(self, ticket_number, owner):
        ticket = self.ticket_get(ticket_number)
        attributes = ticket[3]
        attributes["status"] = "accepted"
        attributes["owner"] = owner
        attributes = self.attrs.edit(attributes, str(ticket_number))
        if attributes:
            attributes_string = self.attrs.dump(attributes)
            comment = self.edit_comment(
                comment="Accepted ticket",
                info=attributes_string,
                prefix="accept_"+str(ticket_number))
            if comment is None:
                return False
            self.server.ticket.update(
                ticket[0],
                comment,
                attributes
            )
            return True
        else:
            return False

    def ticket_sons(self, ticket_number):
        return self.server.ticket.query("parents=~%s" % (ticket_number))

    def ticket_parents(self, ticket_number):
        return self.ticket_get(ticket_number)[3]["parents"]

    def ticket_remaining_time(self, ticket_number):
        ticket = self.ticket_get(ticket_number)
        attributes = ticket[3]
        if attributes["estimatedhours"]:
            hours = int(attributes["estimatedhours"])
        else:
            hours = 0
        return hours

    def ticket_remaining_time_sum(self, ticket_number):
        time = self.ticket_remaining_time(ticket_number)
        for child in self.ticket_sons(ticket_number):
            time += self.ticket_remaining_time_sum(child)
        return time

    def ticket_query_time_sum(self, query):
        tickets = self.server.ticket.query(query)
        time = 0
        for ticket in tickets:
            time += self.ticket_remaining_time(ticket)

        return time

    def ticket_batch_edit(self, id_list):
        for id in id_list:
            ticket = self.ticket_get(id)
            attributes = self.attrs.edit(ticket[3])
            self.server.ticket.update(int(id),
                                      "",
                                      attributes
                                  )

    def ticket_changelog(self, ticket, filter=lambda x:True):
        cl = self.server.ticket.changeLog(ticket)
        return [[ticket] + l for l in cl if filter([ticket] + l)]

    def ticket_recent_changes(self, since, filter=lambda x:True):
        tickets = self.server.ticket.getRecentChanges(since)
        created_tickets = self.server.ticket.query(
            "created=%s.." % (since.strftime("%m/%d/%y"))
        )
        new_filter = lambda log:filter(log) and since <= log[1]
        # from the created tickets. Retrieve only those that have been created
        # after since
        created_tickets_changelogs = []
        for ticket_number in created_tickets:
            ticket = self.ticket_get(ticket_number)
            ticket_log = [ticket_number, ticket[1], ticket[3]["reporter"], "created", "", "", ""]
            if new_filter(ticket_log):
                created_tickets_changelogs.append(
                    ticket_log
                )


        changelogs = []
        for ticket in tickets:
            changelogs = changelogs + self.ticket_changelog(ticket, new_filter)
        return created_tickets_changelogs + changelogs

    def ticket_attachments_put(self, ticket, files_desc, override=False):
        attachments = set(self.ticket_attachments_list(ticket))
        files = set([os.path.basename(fil) for fil in files_desc.keys()])
        # make sure the attachments won't be overridden if not precised
        assert not (attachments.intersection(files) and override)
        done_files = []
        for fil in files_desc:
            basename = os.path.basename(fil)
            content = ""
            with open(fil, "rb") as fil_:
                content = fil_.read()

            done_files.append(
                self.server.ticket.putAttachment(
                    ticket,
                    basename,
                    files_desc[fil],
                    xmlrpclib.Binary(content),
                    True
                )
            )
        return done_files

    def ticket_attachments_list(self, ticket):
        return self.server.ticket.listAttachments(ticket)

    def template_edit(self):
        attributes = \
                     self.attrs.edit(self.template_attributes)
        if attributes:
            self.template_attributes = attributes
            return True
        else:
            return False

    def template_save(self, file_name):
        if os.path.exists(file_name):
            "The file %s will be erased"
            os.unlink(file_name)
        with open(file_name, "w") as file:
            file.write(self.attrs.dump(self.template_attributes))

        return True

    def template_open(self, file_name):
        assert os.path.exists(file_name)
        with open(file_name, "r") as file:
            self.template_attributes = self.attrs.load(file.read())

        return True

    def component_list(self, filter=lambda x:True):
        return [
            comp for comp in self.server.ticket.component.getAll()
            if filter(comp)
        ]

    def milestone_edit(self, milestone_name):
        milestone = self.server.ticket.milestone.get(milestone_name)
        desc = milestone["description"]
        new_desc = edit(desc, prefix=milestone_name.replace(" ", "_"))
        if new_desc:
            self.server.ticket.milestone.update(
                milestone_name,
                {
                    "description":new_desc,
                },
            )
            return True

        return False

    def milestone_list(self, filter=lambda x:True):
        return [
            milestone for milestone in self.server.ticket.milestone.getAll()
            if filter(milestone)
        ]

    def milestone_time_sum(self, milestone_name):
        return self.ticket_query_time_sum("milestone=%s&status=!closed" % milestone_name)
