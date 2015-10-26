"""Virtual host creation in python."""
import string
from random import choice
import subprocess
import crypt
import getpass
import sys
import os
import errno

import MySQLdb as db

# Dirty check for root privileges
try:
    os.rename('/etc/foo', '/etc/bar')
except IOError as error:
    if error[0] == errno.EPERM:
        print >> sys.stderr, "You need root privileges to execute this script."
        sys.exit(1)


def gen_passwd(length=12):
    """Generate password."""
    chars = string.letters + string.digits
    return ''.join(choice(chars) for _ in range(length))


def str_to_bool(text):
    """Convert string to boolean."""
    text = text.lower()
    if text == "yes" or text == "y" or text == "true":
        return True
    else:
        return False


# pylint: disable=too-many-instance-attributes
class VHost(object):

    """Virtual Host."""

    def __init__(self):
        """Set variables to defaults."""
        self.username = ""
        self.password = ""
        self.homedir = ""
        self.skel = ""
        self.mysql = ""
        self.hostnames = ""
        self.nginx = {'ssl': False, 'php': True}
        self.disc_quotum = 100

    def prompt(self):
        """Get data for virtual host."""
        self.username = raw_input("Username: ").lower()

        self.password = gen_passwd()

        self.homedir = raw_input("Homedir[/var/www/%s]: " % self.username)
        if self.homedir == "":
            self.homedir = "/var/www/%s" % self.username

        self.skel = raw_input("Skeleton dir[/var/www/vhostskel]: ")
        if self.skel == "":
            self.skel = "/var/www/vhostskel"

        self.mysql = str_to_bool(raw_input("Create database? (yes/no): "))
        self.hostnames = raw_input("Hostname(s) (space separated): ")

        self.nginx = {
            'ssl': str_to_bool(raw_input("Use ssl (yes/no): ")),
            'php': str_to_bool(raw_input("Use php (yes/no): "))}

        self.disc_quotum = int(raw_input("Disc quotum (in MB): "))

    def create(self):
        """After confirming the details, create the virtual host."""
        try:
            subprocess.check_call([
                "useradd",
                "-d", self.homedir,  # home directory
                "-k", self.skel,  # skeleton directory for homedir
                "-m",  # create home directory if it doesn't exist
                "-p", crypt.crypt(self.password, "22"),  # encrypted password
                self.username])
        except (OSError, subprocess.CalledProcessError) as error:
            print "Failed to create user account.", error
            return 1
        else:
            print "User creation successful!"

        # mysql
        # pylint: disable=no-member
        try:
            mysql_pass = getpass.getpass("Password for mysql root user: ")
            connection = db.connect(
                host="localhost",
                username="root",
                passwd=mysql_pass)
            cursor = connection.cursor()
            if len(self.username) > 16:
                dbuser = self.username[0:16]
            else:
                dbuser = self.username
            sql = "create database %s;\n" % dbuser
            sql += "grant all privileges on %s.* " % dbuser
            sql += "to %s@\"localhost\" " % dbuser
            sql += "identified by \"%s\";\n" % self.password
            sql += "flush privileges;\n"
            cursor.execute(sql)
            cursor.close()
            connection.close()
        except db.Error as error:
            print "Database creation failed:"
            print "Error %d: %s" % (error.args[0], error.args[1])
            print "Try executing the sql manually:"
            print sql
        else:
            print "Database creation successful!"

        # nginx conf - work with templates
        if self.nginx["ssl"] and self.nginx["php"]:
            config = "nginx-php-ssl.template"
        elif self.nginx["ssl"]:
            config = "nginx-ssl.template"
        elif self.php["php"]:
            config = "nginx-php.template"
        else:
            config = "nginx.template"

        # TODO: catch errors so we know if config was created successfully
        with open(config, "r") as source:
            template = string.Template(source.read())
            template.substitute(
                hostnames=self.hostnames,
                username=self.username)
            path = os.path.join("/etc/nginx/sites-available", self.username)
            with open(path, "w") as config:
                config.write(template)

        print "Nginx config created"

        # now link this config file in sites-enabled and restart nginx
        try:
            subprocess.call_check([
                "ln",
                "-s",
                path,
                "/etc/nginx/sites-enabled/."])
        except (OSError, subprocess.CalledProcessError) as error:
            print "Failed to create symlink in /etc/nginx/sites-enabled", error
        else:
            print "Created symlink to enable virtual host."

        # disc quota
        try:
            subprocess.call_check([
                "setquota",
                "-u", self.username,
                self.disc_quotum * 5,  # soft limit (blocks)
                int(self.disc_quotum * 5 * 1.5),  # hard limit (blocks)
                0,  # soft limit (inodes)
                0,  # hard limit (inodes)
                "-a"])  # on all volumes in /etc/mtab
        except (OSError, subprocess.CalledProcessError) as error:
            print "Failed to set disc quotum.", error

        # mail summary to specified addresses, preferably using pgp

        return 0

    def __str__(self):
        """Display data."""
        result = "Username: %s\n" % self.username
        result += "Password: %s\n" % self.password
        result += "Home directory: %s\n" % self.homedir
        result += "Skeleton directory: %s\n" % self.skel
        result += "Create database: %s\n" % self.mysql
        result += "Hostnames: %s\n" % self.hostnames
        result += "Nginx: %s\n" % self.nginx
        result += "Disc quotum: %sMB" % self.disc_quotum
        return result


VHOST = VHost()

VHOST.prompt()

print ""
print VHOST

print ""
raw_input("Cancel by pressing Ctrl-C or confirm by pressing Enter")
print ""

sys.exit(VHOST.create())
