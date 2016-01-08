#!/usr/bin/python
"""Upgrade all wp installations at once."""

import subprocess
import argparse
import os
import sys
import errno

from colorlog import log

# Dirty check for root privileges
try:
    os.rename('/etc/foo', '/etc/bar')
except (OSError, IOError) as error:
    if error[0] == errno.EPERM:
        log("fail", "You need root privileges to execute this script.")
        sys.exit(1)

# I don't care about constant naming in short scripts.
# I kinda hate typing in all caps.
# pylint: disable=invalid-name
parser = argparse.ArgumentParser(
    prog="upgradewp",
    description="Upgrade all wordpress installations in one go.")
parser.add_argument(
    'action',
    choices=[
        "system",
        "plugin",
        "theme"],
    help="upgrade a plugin, a theme, or wordpress itself (system)")
parser.add_argument(
    '-l',
    '--language',
    type=str,
    default="ENG",
    help="what language the upgrade is you're providing (system)")
parser.add_argument(
    '-f',
    '--fail',
    action='store_true',
    help="halt execution at non-fatal error")
parser.add_argument(
    'upgrade',
    type=str,
    help="path to the upgrade you want to apply (expects .zip or .tar.gz)")


args = parser.parse_args()

installations = []

try:
    with open("/etc/pyvhost/wordpress", 'r') as mfile:
        installations = mfile.read().split("\n")
except (OSError, IOError) as error:
    log("fail", "Couldn't open /etc/pyvhost/wordpress")
    log("fail", error)
    sys.exit(1)

upgraded = []

for wordpress in installations:
    if wordpress == "" or wordpress.startswith("#"):
        # log("info", "Empty entry in /etc/pyvhost/wordpress")
        continue
    # [0] = language [1] = path to root [2] = domain
    install = wordpress.split(" ")
    unpack_path = install[1]
    if args.action == "system":
        # perform system upgrade, but only if language matches
        if args.language != install[0]:
            # no go, language mismatches
            # it would be kinda awkward if all your wordpress
            # installations suddenly changed language at install
            # log("info", "Skipping %s - wrong language" % install[1])
            continue
    elif args.action == "plugin":
        # upgrade plugin
        unpack_path = os.path.join(unpack_path, "wp-content/plugins")
    elif args.action == "theme":
        # upgrade theme
        unpack_path = os.path.join(unpack_path, "wp-content/themes")
    else:
        log("fail", "Unknown action.")
        if args.fail:
            sys.exit(1)
        continue

    if args.upgrade.endswith(".zip"):
        try:
            subprocess.check_call([
                "unzip",
                "-o",  # overwrite stuff without prompting
                "-qq",  # work quietly
                "%s" % args.upgrade,
                "-d",  # extraction path
                "%s" % unpack_path])
        except (OSError, subprocess.CalledProcessError) as error:
            log("fail", "Unpacking upgrade failed for %s." % install[1])
            log("fail", error)
            if args.fail:
                sys.exit(1)
        else:
            log("ok", "Successfully extracted %s." % install[1])
            upgraded.append(install[2])
    elif args.upgrade.endswith(".tar.gz"):
        try:
            subprocess.check_call([
                "tar",
                "-xf",  # extract file
                "%s" % args.upgrade,
                "-C",  # extraction directory
                "%s" % unpack_path])
        except (OSError, subprocess.CalledProcessError) as error:
            log("fail", "Unpacking upgrade failed for %s." % install[1])
            log("fail", error)
            if args.fail:
                sys.exit(1)
        else:
            log("ok", "Successfully upgraded %s." % install[1])
            upgraded.append(install[2])
    else:
        log("fail", "Unknown extension")
        sys.exit(1)

    # now move everything from wordpress/ to .
    try:
        subprocess.check_call([
            "mv",
            "%s" % os.path.join(unpack_path, "wordpress", "*"),
            "%s" % unpack_path])
    except (OSError, subprocess.CalledProcessError) as error:
        log("fail", "Couldn't move stuff from wordpress to root dir.")
        log("fail", error)
    else:
        log("ok", "Successfully moved files from wordpress to root dir.")
    # remove wordpress directory
    try:
        subprocess.check_call([
            "rm",
            "-r",
            "%s" % os.path.join(unpack_path, "wordpress")])
    except (OSError, subprocess.CalledProcessError) as error:
        log("fail", "Failed to remove wordpress directory.")
        log("fail", error)
    else:
        log("ok", "Successfully removed wordpress directory")

    # now chown the directory in question to the correct user!
    user = install[1].split("/")[2]
    if install[1].split("/")[1] != "etc":  # don't chown stuff in /etc
        try:
            subprocess.check_call([
                "chown",
                "-R",
                "%s:" % user,
                "%s" % unpack_path])
        except (OSError, subprocess.CalledProcessError) as error:
            log("fail", "Failed to set directory owner properly")
            log("fail", error)

log("info", "Visit the following domains for database updates:")
for domain in upgraded:
    if domain != "-":
        log("info", "\t%s/sesam-enter" % domain)
