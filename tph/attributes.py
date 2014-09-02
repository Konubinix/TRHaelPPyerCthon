#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from edit import edit
import re
import logging
logging.basicConfig()
logger = logging.getLogger(__file__)

class TPHAttributes(object):
    """Class helping the edition of ticket attributes
    """

    def __init__(self, fields):
        """

        Arguments:
        - `fields`: The fields of the attributes to take into account. Not all
        the fields are relevant for edition. For instance, _ts or datetime are
        not meant to be edited.
        """
        self.fields = fields
        self.filter_exception = ["_ts",]

    def dump(self, attributes, ignore_empty=False):
        """From a dictionary of attributes, return a string to be edited.

        Arguments:
        - `attributes`:A dictionary of attribute, such that the one got in a
        ticket.
        - `ignore_empty`:If true, do not display anything for empty fields.
        """
        content = ""
        for field in self.fields:
            value = attributes.get(field, "")
            if value is None:
              value = ""
            if value or not ignore_empty:
                content = content + field+"="+value+"\n"
        content = content + attributes.get("description", "")
        return content

    def load(self, string):
        """From a string, return a dictionary of attributes to be given in any
        of the ticket update or creation methods.

        The string should be in the format generated by the `dump` method.

        Arguments:
        - `string`:A string got by self.dump(attributes).
        """
        attributes = {}
        content = string.splitlines()
        field_regexp = "^([^= ]+)=(.*)$"
        match = re.match(field_regexp, content[0])
        while match:
            field_name = match.group(1)
            field_value = match.group(2)
            attributes[field_name] = field_value
            content.pop(0)
            if len(content) > 0:
                match = re.match(field_regexp, content[0])
            else:
                match = None

        # the remaining of the content is the description
        description = "\n".join(content)
        if description:
            # avoid emptying the description
            attributes["description"] = description
        return attributes

    def edit(self, attributes, prefix="", ignore_empty=False):
        """Edit a list of ticket attributes by editing a temporary file.

        The particular attribute _ts is not edited and put back as is in the
        returned attributes. It is used internally in trac to resolve
        conflicts.

        Returns the new list of attributes.

        Arguments:
        - `attributes`:The list of attributes to edit.
        - `prefix`:The prefix of the temporary file. It might be useful to put
        meaningful information in here such as the ticket number so that the
        user knows the attributes of what ticket (s)he is editing.
        - `ignore_empty`:See self.dump.
        """
        attributes_string = edit(
            self.dump(attributes, ignore_empty=ignore_empty),
            prefix=prefix+"_"
        )
        if attributes_string == "":
            return None

        new_attributes = self.load(attributes_string)
        if attributes.get("_ts", None):
            new_attributes["_ts"] = attributes["_ts"]
        return new_attributes

    def merge(self, old, new, only_new_fields=False):
        """Add the information of new attributes into the old ones. For most of
the attributes work, the value is replaced in the old value by the new one."""
        result_fields = {}
        for key in list(new.keys()):
            if key in ("keywords", "cc"):
                if new[key] == "":
                    new_values = set()
                else:
                    new_values = set(re.split("[ ,]+", new[key]))
                if old[key] == "":
                    old_values = set()
                else:
                    old_values = set(re.split("[ ,]+", old[key]))
                # value -> toggle the value
                # +value -> add the value
                # -value -> remove the value
                for value in new_values:
                    if value.startswith("+"):
                        old_values.add(value[1:])
                    elif value.startswith("-"):
                        if value[1:] in old_values:
                            old_values.remove(value[1:])
                    else:
                        if value in old_values:
                            old_values.remove(value)
                        else:
                            old_values.add(value)
                result_fields[key] = " ".join(list(old_values))
            else:
                result_fields[key] = new[key]
            if not only_new_fields:
                old[key] = result_fields[key]
        if only_new_fields:
            return result_fields
        else:
            return old

    def filter(self, attributes):
        """Removing any attribute in attributes that is not in the recognize
        fields but keep attributes whose key is in self.filter_exception"""
        return {
            _key : attributes[_key] for _key in attributes
            if _key in self.fields or _key in self.filter_exception
        }
