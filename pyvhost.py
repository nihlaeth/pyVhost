#!/usr/bin/python
"""Virtual host creation in python."""
import string
from random import choice
import subprocess
import crypt
import getpass
import sys
import os
import errno
import random

from colorlog import log

import MySQLdb as db
import gnupg
from email.mime.text import MIMEText
import argparse
from crontab import CronTab


# Dirty check for root privileges
try:
    os.rename('/etc/foo', '/etc/bar')
except (OSError, IOError) as error:
    if error[0] == errno.EPERM:
        log("fail", "You need root privileges to execute this script.")
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


def cap16(text):
    """Return string of max length 16."""
    if len(text) > 16:
        return text[0:16]
    else:
        return text


# pylint: disable=too-many-instance-attributes
class VHost(object):

    """Virtual Host."""

    def __init__(self):
        """Set variables to defaults."""
        self.username = ""
        self.domain = ""
        self.dbuser = ""
        self.password = ""
        self.homedir = ""
        self.skel = ""
        self.hostnames = ""
        self.nginx = {
            'ssl': False,
            'sslred': False,
            'php': False,
            'wp': False,
            'wwwred': False}
        self.disc_quotum = 100
        self.mailto = ""

    def prompt(self, to_do):
        """Get data for virtual host."""
        self.username = raw_input("Username: ").lower()

        if to_do['domain'] or to_do['nginx'] or to_do['mysql']:
            self.domain = raw_input("Domain name: ").lower()

        if to_do['user'] or to_do['mysql']:
            self.password = gen_passwd()

        if to_do['mysql']:
            self.dbuser = cap16(self.domain).replace(".", "_").replace("-", "_")

        self.homedir = raw_input("Homedir[/home/%s]: " % self.username)
        if self.homedir == "":
            self.homedir = "/home/%s" % self.username

        if to_do['user']:
            self.skel = raw_input("Skeleton dir[/home/vhostskel]: ")
            if self.skel == "":
                self.skel = "/home/vhostskel"

            try:
                self.disc_quotum = int(raw_input("Disc quotum (in MB): "))
            except ValueError:
                log("warn", "Invalid entry - disc quotum set to 0")
                self.disc_quotum = 0

        if to_do['nginx']:
            self.hostnames = raw_input("Server name(s) (space separated): ")

            self.nginx = {
                'ssl': str_to_bool(raw_input("Use ssl (yes/no): ")),
                'sslred': str_to_bool(raw_input(
                    "Redirect to https? (yes/no): ")),
                'sslcert': str_to_bool(raw_input(
                    "Create self-signed certificates? (yes/no): ")),
                'wwwred': str_to_bool(raw_input(
                    "Redirect to www? (yes/no): ")),
                'php': str_to_bool(raw_input("Use php (yes/no): ")),
                'ipv6': str_to_bool(raw_input("Use ipv6 (yes/no): ")),
                'wp': str_to_bool(raw_input("Wordpress settings? (yes/no): "))}

        self.mailto = raw_input("Mail summary to: ")

    def create_db(self):
        """Create database."""
        # pylint: disable=no-member
        mysql_pass = getpass.getpass("Password for mysql root user: ")
        sql = "create database %s;\n" % self.dbuser
        sql += "grant all privileges on %s.* " % self.dbuser
        sql += "to %s@'localhost' " % self.dbuser
        sql += "identified by '%s';\n" % self.password
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
            log("fail", "Database creation failed:")
            log("fail", "Error %d: %s" % (error.args[0], error.args[1]))
            log("info", "Try executing the sql manually:")
            log("info", sql)
        else:
            log("ok", "Database creation successful!")
        # now set backup script
        command = "mysqldump -h 127.0.0.1 "
        command += "--user %s " % self.dbuser
        command += "--password=%s " % self.password
        command += "%s > " % self.dbuser
        command += "%s/" % os.path.join(self.homedir, self.domain, "backup")
        command += "%s-dump-" % self.dbuser
        command += "`date \"+%Y-%m-%d-%H-%M\"`.sql"
        dbrotate = "find %s" % os.path.join(
            self.homedir,
            self.domain,
            "backup")
        dbrotate += " -type f -mtime +2|xargs -i rm -f {}"
        cron = CronTab(user=self.username)
        backup = cron.new(command=command)
        minute = random.choice(range(60))
        hour = random.choice(range(24))
        backup.setall("%d %d * * *" % (minute, hour))
        rotate = cron.new(command=dbrotate)
        minute = random.choice(range(60))
        hour = random.choice(range(24))
        rotate.setall("%d %d * * *" % (minute, hour))
        try:
            assert backup.is_valid() == True
            assert rotate.is_valid() == True
        except AssertionError:
            log("fail", "Invalid cron command for db backups.")
        else:
            cron.write_to_user(user=self.username)
            log("ok", "Added cron for db backup and backup rotation.")

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
            log("fail", "Failed to create user account.")
            log("fail", error)
            return 1
        else:
            log("ok", "User creation successful!")

    def create_domain(self):
        """Create domain folder inside user account."""
        try:
            subprocess.check_call([
                "mkdir",
                "-p",
                os.path.join(self.homedir, self.domain, "www")])
        except (OSError, subprocess.CalledProcessError) as error:
            log("fail", "Failed to create domain folder.")
            log("fail", error)
        else:
            log("ok", "Created domain folder.")

        try:
            subprocess.check_call([
                "mkdir",
                "-p",
                os.path.join(self.homedir, self.domain, "backup")])
        except (OSError, subprocess.CalledProcessError) as error:
            log("fail", "Failed to create backup folder.")
            log("fail", error)
        else:
            log("ok", "Created backup folder.")

        try:
            subprocess.check_call([
                "chown",
                "-R",
                self.username + ":",
                os.path.join(self.homedir, self.domain)])
        except (OSError, subprocess.CalledProcessError) as error:
            log("fail", "Failed to chown domain folder.")
            log("fail", error)
        else:
            log(
                "ok",
                "Set %s as owner of domain folder." % self.username)

    def create_nginx(self):
        """Create nginx config file."""
        docroot = os.path.join(self.homedir, self.domain, "www")
        try:
            with open("/usr/share/pyVhost/default", "r") as source_file:
                template = string.Template(source_file.read())
                template = template.safe_substitute(
                    hostnames=self.hostnames,
                    domain=self.domain,
                    docroot=docroot,
                    ssl="" if self.nginx["ssl"] else "#",
                    sslred="" if self.nginx["sslred"] else "#",
                    nosslred="#" if self.nginx["sslred"] else "",
                    wp="" if self.nginx["wp"] else "#",
                    nowp="#" if self.nginx["wp"] else "",
                    php="" if self.nginx["php"] else "#",
                    nophp="#" if self.nginx["php"] else "",
                    wwwred="" if self.nginx["wwwred"] else "#",
                    ipv6="" if self.nginx["ipv6"] else "#")
                path = os.path.join(
                    "/etc/nginx/sites-available",
                    self.domain)
                with open(path, "w") as config_file:
                    config_file.write(template)
        except (OSError, IOError) as error:
            log("fail", "Failed to create config file for nginx.")
            log("fail", error)
        else:  # only attempt symlink creation and nginx restart at success
            log("ok", "Nginx config created")

            # if indicated, create self-signed certificates
            if self.nginx["sslcert"]:
                try:
                    subprocess.check_call([
                        "openssl",
                        "req",
                        "-new",
                        "-x509",
                        "-sha256",
                        "-days",
                        "365",
                        "-nodes",
                        "-newkey",
                        "rsa:2048",
                        "-out",
                        os.path.join("/etc/nginx/certs", self.domain + ".pem"),
                        "-keyout",
                        os.path.join("/etc/nginx/certs", self.domain + ".key")
                        ])
                except (OSError, subprocess.CalledProcessError) as error:
                    log("fail", "Failed to create certificates.")
                    log("fail", error)
                else:
                    log("ok", "Created self-signed certificates.")

            # now link this config file in sites-enabled and restart nginx
            try:
                subprocess.check_call([
                    "ln",
                    "-s",
                    path,
                    "/etc/nginx/sites-enabled/."])
            except (OSError, subprocess.CalledProcessError) as error:
                log("fail", "Failed to create symlink.")
                log("fail", error)
            else:
                log("ok", "Created symlink to enable virtual host.")

            try:
                subprocess.check_call([
                    "/etc/init.d/nginx",
                    "configtest"])
            except (OSError, subprocess.CalledProcessError) as error:
                log("fail", "Invalid nginx config - fix manually!")
                log("fail", error)
            else:
                log("ok", "Nginx config valid - now restarting nginx...")
                try:
                    subprocess.check_call([
                        "/etc/init.d/nginx",
                        "restart"])
                except (OSError, subprocess.CalledProcessError) as error:
                    log("fail", "Failed to restart nginx.")
                    log("fail", error)
                else:
                    log("ok", "Restarted nginx.")
        # Now do some wordpress magic
        # I added this here, because create_nginx has all
        # the right info and it was too much work to separate
        # out the wordpress stuff
        if self.nginx['wp']:
            self.create_wordpress(docroot)

    def create_wordpress(self, docroot):
        """Arrange all the wordpress stuff."""
        lang = str(raw_input(
            "Choose wordpress language. (eng/nl)[eng]: "))
        if lang == "":
            lang = "eng"
        # add to /etc/pyvhost/wordpress list for maintenance
        try:
            line = "%s %s %s" % (lang.upper(), docroot, self.domain)
            line_pres = False
            with open("/etc/pyvhost/wordpress", 'r') as mfile:
                content = mfile.read().split('\n')
                for rule in content:
                    if rule == line:
                        line_pres = True
                if not line_pres:
                    content.append(line)
            with open("/etc/pyvhost/wordpress", 'w') as mfile:
                mfile.write('\n'.join(content))
        except (OSError, IOError) as error:
            log(
                "fail",
                "Failed to add domain to wordpress maintenance list")
            log("fail", error)
            log(
                "info",
                "Try adding this line to /etc/pyvhost/wordpress manually:")
            log("info", "%s %s %s\n" % (
                lang.upper(),
                docroot,
                self.domain))
        else:
            log("ok", "Added domain to wordpress maintenance list.")

        # install wordpress if necessary
        install = str_to_bool(raw_input("Install wordpress? (y/n): "))
        if install:
            try:
                subprocess.check_call(
                    "cp -r /etc/pyvhost/wp-%s/* %s/." % (lang, docroot),
                    shell=True)
            except (OSError, subprocess.CalledProcessError) as error:
                log("fail", "Failed to copy wordpress files to docroot.")
                log("fail", error)
            else:
                log("ok", "Copied wordpress files to docroot.")

    def set_disc_quota(self):
        """Set disc quota."""
        try:
            subprocess.check_call([
                "setquota",
                "-u", self.username,
                str(self.disc_quotum * 1024),  # soft limit (blocks)
                str(int(self.disc_quotum * 1024 * 1.5)),  # hard limit (blocks)
                "0",  # soft limit (inodes)
                "0",  # hard limit (inodes)
                "-a"])  # on all volumes in /etc/mtab
        except (OSError, subprocess.CalledProcessError) as error:
            log("fail", "Failed to set disc quotum.")
            log("fail", error)

    def mail_summary(self):
        """Send a summary to specified mail addresses via pgp if possible."""
        gpg = gnupg.GPG(gnupghome='/root/.gnupg')
        encrypted_data = gpg.encrypt(str(self), self.mailto, always_trust=True)
        if encrypted_data.status != "encryption ok":
            # pylint: disable=no-member
            log("fail", "PGP encryption failed.")
            log("fail", encrypted_data.status)
            log("fail", encrypted_data.stderr)
            log("info", "Do you want to send the summary unencrypted instead?")
            raw_input("Press Ctrl-C to cancel, press Enter to continue.")
            msg = MIMEText(str(self))
        else:
            msg = MIMEText(str(encrypted_data))
        msg["From"] = "bestuur@humanity4all.nl"
        msg["To"] = self.mailto
        msg["Subject"] = "Virtual host (%s:%s) created" % (
            self.username,
            self.domain)
        try:
            pipe = subprocess.Popen(
                ["/usr/sbin/sendmail", "-t", "-oi"],
                stdin=subprocess.PIPE)
            pipe.communicate(msg.as_string())
        except OSError as error:
            log("fail", "Failed to send summary email.")
            log("fail", error)
        else:
            log("ok", "Summary email sent.")

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

        log("header", "#########################")
        log("header", "#        Summary        #")
        log("header", "#########################")
        log("header", "")
        log("info", self)
        log("info", "")
        log("info", to_do)
        log("info", "")
        if to_do['nginx']:
            log(
                "warn",
                ("WARNING: this will overwrite nginx "
                 "config if the file exists!"))
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
        result = "===================\n"
        result += "==   Account     ==\n"
        result += "===================\n"
        result += "Username: %s\n" % self.username
        result += "Home directory: %s\n" % self.homedir
        result += "Skeleton directory: %s\n" % self.skel
        result += "Disc quotum: %dMB\n" % self.disc_quotum
        result += "===================\n"
        result += "==    Domain     ==\n"
        result += "===================\n"
        result += "Domain: %s\n" % self.domain
        result += "Server name(s): %s\n" % self.hostnames
        result += "Nginx: %s\n" % self.nginx
        result += "===================\n"
        result += "==    Mysql      ==\n"
        result += "===================\n"
        result += "Database(user): %s\n" % self.dbuser
        result += "Password: %s\n" % self.password

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
    help=(
        "create-user creates a user (with disc quotum) and nothing else | "
        "add-domain adds domain to existing user account, includes "
        "database and nginx config creation | "
        "create-db creates database, nothing else | "
        "create-nginx-config creates nginx config file, nothing else | "
        "all does all of the above"))

ARGS = PARSER.parse_args()
VHOST = VHost()

sys.exit(VHOST.create(ARGS.action))
