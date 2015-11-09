#!/usr/bin/python
"""Install necessary config files and symlinks for pyvhost tools."""
import sys
import errno
import os

from colorlog import log

import subprocess

# pylint: disable=invalid-name

# Dirty check for root privileges
try:
    os.rename('/etc/foo', '/etc/bar')
except (OSError, IOError) as error:
    if error[0] == errno.EPERM:
        log("fail", "You need root privileges to execute this script.")
        sys.exit(1)

# Create /etc/pyvhost folder
try:
    subprocess.check_call([
        "mkdir",
        "-p",  # no error if exists
        "/etc/pyvhost"])
except (OSError, subprocess.CalledProcessError) as error:
    log("fail", "Failed to create /etc/pyvhost")
    log("fail", error)
else:
    log("ok", "Created /etc/pyvhost folder")

# Create wordpress maintenance file
# First, touch it to make sure it exists
try:
    subprocess.check_call([
        "touch",
        "/etc/pyvhost/wordpress"])
except (OSError, subprocess.CalledProcessError) as error:
    # It probably already exists, no matter.
    # Any other errors will some to light later.
    pass

try:
    with open("/etc/pyvhost/wordpress", "r") as mfile:
        content = mfile.read().split("\n")
        comment = "# LANG docroot domain"
        line_nl = "NL /etc/pyvhost/wp-nl -"
        line_eng = "ENG /etc/pyvhost/wp-eng -"
        comment_pres = False
        nl_pres = False
        eng_pres = False
        for line in content:
            if line == line_nl:
                nl_pres = True
            elif line == line_eng:
                eng_pres = True
            elif line == comment:
                comment_pres = True
        if not nl_pres:
            content = [line_nl] + content
        if not eng_pres:
            content = [line_eng] + content
        if not comment_pres:
            content = [comment] + content
    with open("/etc/pyvhost/wordpress", "w") as mfile:
        mfile.write('\n'.join(content))
except (OSError, IOError) as error:
    log("fail", "Could not create wordpress maintenance list")
    log("fail", error)
else:
    log("ok", "Wordpress maintenance file OK.")

# Create symlinks in /usr/bin
scriptdir = os.path.dirname(os.path.realpath(__file__))
try:
    subprocess.check_call([
        "ln",
        "-sf",
        "%s" % os.path.join(scriptdir, "pyvhost.py"),
        "/usr/bin/pyvhost"])
except (OSError, subprocess.CalledProcessError) as error:
    log("fail", "Failed to create a symlink to pyvhost.py")
    log("fail", error)
else:
    log("ok", "Creates symlink to pyvhost.py (pyvhost)")

try:
    subprocess.check_call([
        "ln",
        "-sf",
        "%s" % os.path.join(scriptdir, "upgradewp.py"),
        "/usr/bin/upgradewp"])
except (OSError, subprocess.CalledProcessError) as error:
    log("fail", "Failed to create a symlink to upgradewp.py")
    log("fail", error)
else:
    log("ok", "Creates symlink to upgradewp.py (upgradewp)")

try:
    subprocess.check_call([
        "ln",
        "-sf",
        "%s" % os.path.join(scriptdir, "threatcheck.py"),
        "/usr/bin/threatcheck"])
except (OSError, subprocess.CalledProcessError) as error:
    log("fail", "Failed to create a symlink to threatcheck.py")
    log("fail", error)
else:
    log("ok", "Creates symlink to threatcheck.py (threatcheck)")

log("warn", "Now please install template wordpress installations,")
log("warn", "including desired plugins and themes, under:")
log("warn", "\t/etc/pyvhost/wp-eng")
log("warn", "\t/etc/pyvhost/wp-nl")
