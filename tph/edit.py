#!/usr/bin/env python
# -*- coding:utf-8 -*-

import tempfile
import os
import subprocess

def edit(content, suffix=".wiki", prefix=""):
    """Edit content, using a temporary file.

    The environment variable EDITOR is used to edit the temporary file.

    Arguments:
    - `content`:The content to edit.
    - `suffix`:The suffix of the temporary file.
    - `prefix`:The prefix of the temporary file.
    """
    temp_file = tempfile.NamedTemporaryFile(prefix=prefix, suffix=suffix, delete=False)
    temp_file.write(content.encode("utf-8"))
    temp_file.close()
    rc = subprocess.call([os.environ["EDITOR"], temp_file.name])
    if rc == 0:
        # get the new content and return it
        with open(temp_file.name, "r") as tfile:
            new_content = tfile.read().decode("utf-8")
    else:
        new_content = None

    os.unlink(temp_file.name)
    return new_content
