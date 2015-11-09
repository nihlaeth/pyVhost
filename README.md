# pyVhost
Toolset for working with virtual hosts using nginx

Adding yet another website to your server can be
tedious, as is maintaining them.

That's why I created these scripts - to
consolidate some repetitive actions. It's meant
for my own system (debian 8.something), not for
general use, but feel free to adapt it for your
own system and practices.

## Usage
I don't provide extensive support (though feel
free to ask questions), so it feels a bit misleading
to provide usage info for a project that's meant just
for me and my own server(s). So read them with this in
mind.

### Installation
  python install.py

The installation script informs you of further steps to
take, namely making two template installations of wordpress
that will get copied when creating a new virtual host with
wordpress. I use two languages, english and dutch.

The english installation goes into /etc/pyvhost/wp-eng,
the dutch goes into /etc/pyvhost/wp-nl. Directly inside
these directories, you should see a host of wp-[something].php
files, not a directory named wordpress (unless you want all your
wordpress installations to be under yourdomain.com/wordpress/

### pyvhost
Pyvhost is used to create new virtual hosts, and on occasion
to overwrite outdated config files. For usage info, try:
  pyvhost -h

### threatcheck
Threatcheck is used to scan for potentially malicious php code,
often found in wordpress themes, plugins, and compromised wordpress
installations. It's not fool proof, but it could at least point
you in the direction of files that need a closer look. For usage
info, try:
  threatcheck -h

### upgradewp
Why execute the same command 30, 50 or even 150 times, when you can
have a script do it? Wordpress updates are tedious, and this takes
care of all your wordpress installations (at least the ones installed
with pyvhost - you can add them manually in /etc/pyvhost/wordpress).
You can upgrade plugins and themes, and even mass-install them. And
you can upgrade your wordpress installations themselves, one language
at the time. Keep in mind, you still have to do the database upgrades
from your browser, one installation at the time. This helpful script
even provides you with a list of urls you need to visit. For usage
info, try:
  upgradewp -h

## Easy customizations
You probably use different nginx settings. To customize those, simply
edit "default". Variables are started with a $, $$ gets translated to
a single $ in the final config file.

Good luck!
