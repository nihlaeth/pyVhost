#!/usr/bin/python
"""Because so many malicious php code uses base64_decode."""

import subprocess
import sys


# Not going with valid constant names here, it's a small script
# pylint: disable=invalid-name
# List all files
find = subprocess.Popen(
    ('find', str(sys.argv[1]), '-type', 'f'),
    stdout=subprocess.PIPE)

# Find any with php in the title to narrow it down a bit
# Really, files without php in their title could still be executed
# via includes, but that's relatively rare
grep = subprocess.Popen(
    ('grep', 'php'),
    stdin=find.stdout,
    stdout=subprocess.PIPE)

# Now grep any php file for the occurance of base64_decode
xargs = subprocess.Popen((
    'xargs',
    '-I{}',
    'grep',
    '-l',
    'base64_decode',
    '{}'), stdin=grep.stdout, stdout=subprocess.PIPE)
find.stdout.close()
grep.stdout.close()

data = xargs.communicate()[0]
if data is not None:
    data = data.split("\n")
else:
    data = []

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
