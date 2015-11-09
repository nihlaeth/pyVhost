#!/usr/bin/python
"""Because so much malicious php code uses base64_decode."""

import subprocess
import sys
import argparse


# Not going with valid constant names here, it's a small script
# pylint: disable=invalid-name

parser = argparse.ArgumentParser(
    prog="threatcheck",
    description="Check for suspicious php code")
parser.add_argument(
    'path',
    type=str,
    help="path to scan")

args = parser.parse_args()

# First, find all files (not directories) in the path provided,
# with php in their name (case insensitive). Then grep the accumulated
# file list for occurences of base64_decode and return filenames of the
# positives.
cmd = 'find %s ' % args.path
cmd += '-type f '
cmd += '-iname \'*php*\' '
cmd += '-exec '
cmd += 'grep -l base64_decode {} +'
data = subprocess.check_output(cmd, shell=True).split('\n')

valid_files = (
    # wordpress files that should contain base64_decode
    "/wp-content/plugins/all-in-one-seo-pack/OAuth.php",
    "/wp-content/plugins/better-wp-security/core/class-itsec-core.php",
    "/wp-includes/class-smtp.php",
    "/wp-includes/class-IXR.php",
    "/wp-includes/class-phpmailer.php",
    "/wp-includes/SimplePie/Sanitize.php",
    "/wp-includes/class-wp-customize-widgets.php",
    "/wp-includes/ID3/module.audio.ogg.php",
    "/wp-includes/class-feed.php",
    "/wp-admin/includes/file.php",
    # smf files that should contain base64_decode
    "/Sources/Subs-Post.php",
    "/Sources/Search.php",
    "/Sources/ManageErrors.php",
    "/Sources/Articles.php",
    "/Sources/PersonalMessage.php",
    "/Sources/Modlog.php",
    "/Sources/Subs-OpenID.php",
    "/Sources/Subs-Menu.php",
    "/Sources/Subs-Editor.php",
    "/Sources/Packages.php",
    "/Sources/ManageMembers.php",
    "/Sources/Calendar.php",
    "/Sources/Articles2.php",
    # mediawiki files that should contain base64_decode
    "/includes/password/EncryptedPassword.php",
    "/includes/password/Pbkdf2Password.php",
    "/includes/Import.php",
    "/extensions/SyntaxHighlight_GeSHi/geshi/geshi/gml.php",
    "/extensions/SyntaxHighlight_GeSHi/geshi/geshi/php.php",
    "/extensions/SyntaxHighlight_GeSHi/geshi/geshi/php-brief.php")

for entry in data:
    if not entry.endswith(valid_files):
        print entry
