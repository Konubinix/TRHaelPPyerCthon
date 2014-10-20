#!/bin/bash

HERE="$(dirname "$0")"
TRAC_CMDRC="${HERE}/trac_cmdrc_trachacks.conf" trac_cmd.py "$@"
