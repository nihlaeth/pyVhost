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
import gnupg
from email.mime.text import MIMEText
import argparse

# Dirty check for root privileges
try:
    os.rename('/etc/foo', '/etc/bar')
except (OSError, IOError) as error:
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
        self.domain = ""
        self.password = ""
        self.homedir = ""
        self.skel = ""
        self.hostnames = ""
        self.nginx = {'ssl': False, 'php': False}
        self.disc_quotum = 100
        self.mailto = ""

    def prompt(self, to_do):
        """Get data for virtual host."""
        self.username = raw_input("Username: ").lower()

        if to_do['domain']:
            self.domain = raw_input("Domain name: ").lower()

        if to_do['user'] or to_do['mysql']:
            self.password = gen_passwd()

        self.homedir = raw_input("Homedir[/home/%s]: " % self.username)
        if self.homedir == "":
            self.homedir = "/home/%s" % self.username

        if to_do['user']:
            self.skel = raw_input("Skeleton dir[/home/vhostskel]: ")
            if self.skel == "":
                self.skel = "/home/vhostskel"

            self.disc_quotum = int(raw_input("Disc quotum (in MB): "))

        if to_do['nginx']:
            self.hostnames = raw_input("Server name(s) (space separated): ")

            self.nginx = {
                'ssl': str_to_bool(raw_input("Use ssl (yes/no): ")),
                'php': str_to_bool(raw_input("Use php (yes/no): "))}

        self.mailto = raw_input("Mail summary to: ")

    def create_db(self):
        """Create database."""
        # pylint: disable=no-member
        mysql_pass = getpass.getpass("Password for mysql root user: ")
        if len(self.username) > 16:
            dbuser = self.username[0:16]
        else:
            dbuser = self.username
        sql = "create database %s;\n" % dbuser
        sql += "grant all privileges on %s.* " % dbuser
        sql += "to %s@\"localhost\" " % dbuser
        sql += "identified by \"%s\";\n" % self.password
        sql += "flush privileges;\n"
        try:
            connection = db.connect(
                host="localhost",
                user="root",
                passwd=mysql_pass)
            cursor = connection.cursor()
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

    def create_user(self):
        """Create user account."""
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

    def create_domain(self):
        """Create domain folder inside user account."""
        try:
            subprocess.check_call([
                "mkdir",
                "-p",
                os.path.join(self.homedir, self.domain, "www")])
        except (OSError, subprocess.CalledProcessError) as error:
            print "Failed to create domain folder.", error
        else:
            print "Created domain folder."

        try:
            subprocess.check_call([
                "chown",
                "-R",
                self.username + ":",
                os.path.join(self.homedir, self.domain)])
        except (OSError, subprocess.CalledProcessError) as error:
            print "Failed to chown domain folder.", error
        else:
            print "Set %s as owner of domain folder." % self.username

    def create_nginx(self):
        """Create nginx config file."""
        if self.nginx["ssl"] and self.nginx["php"]:
            config = "nginx-php-ssl.template"
        elif self.nginx["ssl"]:
            config = "nginx-ssl.template"
        elif self.nginx["php"]:
            config = "nginx-php.template"
        else:
            config = "nginx.template"

        try:
            with open(config, "r") as source_file:
                template = string.Template(source_file.read())
                template.substitute(
                    hostnames=self.hostnames,
                    domain=self.domain,
                    docroot=os.path.join(self.homedir, self.domain, "www"))
                path = os.path.join(
                    "/etc/nginx/sites-available",
                    self.domain)
                with open(path, "w") as config_file:
                    config_file.write(template)
        except (OSError, IOError) as error:
            print "Failed to create config file for nginx.", error
        else:  # only attempt symlink creation and nginx restart at success
            print "Nginx config created"
            # now link this config file in sites-enabled and restart nginx
            try:
                subprocess.check_call([
                    "ln",
                    "-s",
                    path,
                    "/etc/nginx/sites-enabled/."])
            except (OSError, subprocess.CalledProcessError) as error:
                print "Failed to create symlink.", error
            else:
                print "Created symlink to enable virtual host."
            try:
                subprocess.check_call([
                    "/etc/init.d/nginx",
                    "restart"])
            except (OSError, subprocess.CalledProcessError) as error:
                print "Failed to restart nginx.", error
            else:
                print "Restarted nginx."

    def set_disc_quota(self):
        """Set disc quota."""
        try:
            subprocess.check_call([
                "setquota",
                "-u", self.username,
                str(self.disc_quotum * 5),  # soft limit (blocks)
                str(int(self.disc_quotum * 5 * 1.5)),  # hard limit (blocks)
                "0",  # soft limit (inodes)
                "0",  # hard limit (inodes)
                "-a"])  # on all volumes in /etc/mtab
        except (OSError, subprocess.CalledProcessError) as error:
            print "Failed to set disc quotum.", error

    def mail_summary(self):
        """Send a summary to specified mail addresses via pgp it possible."""
        gpg = gnupg.GPG(gnupghome='/root')
        gpg.encoding = 'utf-8'
        encrypted_ascii_data = gpg.encrypt(
            str(self),
            self.mailto.split(", "),
            always_trust=True)
        if str(encrypted_ascii_data) == "":
            print "No public key available. Send unencrypted?"
            raw_input("Press Ctrl-C to cancel, press Enter to continue.")
            msg = MIMEText(str(self))
        else:
            msg = MIMEText(str(encrypted_ascii_data))
        msg["From"] = "bestuur@humanity4all.nl"
        msg["To"] = self.mailto
        msg["Subject"] = "Virtual host (%s) created" % self.username
        try:
            pipe = subprocess.Popen(
                ["/usr/sbin/sendmail", "-t", "-oi"],
                stdin=subprocess.PIPE)
            pipe.communicate(msg.as_string())
        except OSError as error:
            print "Failed to send summary email.", error
        else:
            print "Summary email sent."

    def create(self, action):
        """Execute appropriate parts after confirmation."""
        to_do = {
            'user': False,
            'domain': False,
            'mysql': False,
            'nginx': False}
        if action == "create-user":
            to_do['user'] = True
        elif action == "add-domain":
            to_do['domain'] = True
            to_do['mysql'] = True
            to_do['nginx'] = True
        elif action == "create-db":
            to_do['mysql'] = True
        elif action == "create-nginx-config":
            to_do['nginx'] = True
        elif action == "all":
            to_do['user'] = True
            to_do['domain'] = True
            to_do['mysql'] = True
            to_do['nginx'] = True

        self.prompt(to_do)

        print "#########################"
        print "#        Summary        #"
        print "#########################"
        print ""
        print self
        print ""
        print to_do
        print ""
        if to_do['nginx']:
            print "WARNING: this will overwrite nginx config if the file exists!"
        raw_input("Cancel by pressing Ctrl-C or confirm by pressing Enter")

        exit_code = 0
        if to_do['user']:
            code = self.create_user()
            exit_code = code if code != 0 else exit_code
            code = self.set_disc_quota()
            exit_code = code if code != 0 else exit_code
        if to_do['domain']:
            code = self.create_domain()
            exit_code = code if code != 0 else exit_code
        if to_do['mysql']:
            code = self.create_db()
            exit_code = code if code != 0 else exit_code
        if to_do['nginx']:
            code = self.create_nginx()
            exit_code = code if code != 0 else exit_code
        code = self.mail_summary()
        exit_code = code if code != 0 else exit_code

        return exit_code

    def __str__(self):
        """Display data."""
        result = "Username: %s\n" % self.username
        result += "Domain: %s\n" % self.domain
        result += "Password: %s\n" % self.password
        result += "Home directory: %s\n" % self.homedir
        result += "Skeleton directory: %s\n" % self.skel
        result += "Hostnames: %s\n" % self.hostnames
        result += "Nginx: %s\n" % self.nginx
        result += "Disc quotum: %sMB" % self.disc_quotum
        return result

PARSER = argparse.ArgumentParser(
    prog="pyVHost",
    description='Create virtual hosts.')
PARSER.add_argument(
    'action',
    choices=[
        "create-user",
        "add-domain",
        "create-db",
        "create-nginx-config",
        "all"],
    help="action the script is to perform")

ARGS = PARSER.parse_args()
print ARGS
VHOST = VHost()

sys.exit(VHOST.create(ARGS.action))
