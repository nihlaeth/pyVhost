"""Virtual host creation in python."""
import string
from random import choice
import subprocess
import crypt
import getpass
import MySQLdb as db


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
        except OSError | subprocess.CalledProcessError, error:
            print "Failed to create user account.", error
            return 1
        else:
            print "User creation successful!"

        # mysql
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
        except db.Error, error:
            print "Database creation failed:"
            print "Error %d: %s" % (error.args[0], error.args[1])
            print "Try executing the sql manually:"
            print sql
        else:
            print "Database creation successful!"

    def __str__(self):
        """Display data."""
        result = "Username: %s\n" % self.username
        result += "Password: %s\n" % self.password
        result += "Home directory: %s\n" % self.homedir
        result += "Create database: %s\n" % self.mysql
        result += "Hostnames: %s\n" % self.hostnames
        result += "Nginx: %s\n" % self.nginx
        result += "Disc quotum: %sMB" % self.disc_quotum
        return result


VHOST = VHost()

VHOST.prompt()

print VHOST
