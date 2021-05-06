PyTrayCharMap
=============

Small PyQt tool in tray to put misc. unicode exotic symbols to clipboard

It shows an icon in tray with tree-like context menu of characters.

Clicking a character appends it to clipboard (when clipboard was modified
by other programs, this characeter replaces its content). By hovering
characters and pressing `space` you can avoid menu hiding, so you
can get a lot of characters in rapid way.

Left-clicking on tray icon shows curent clipboard content.

You are free to modify menu in `menu/charmap.yaml` file.

On UNiX-like system just run `run.sh &`, on Windows `run.bat`.

Installation
============

`pip3 install -r requirements.txt` or `pip3 install --user -r requirements.txt`
or use system package manager depending on your environment.

For Linux and Windows users
---------------------------

Add `run.sh` or `run.bat` script to run at your session startup. In the both Linux and
Windows it is usually easy enough.

For Mac OS users
----------------

For Mac OS users, it can be actually painful to run shell script at user login,
because the environment designed to always keep you in a sort of straitjacket.

Having [Python 3 installed with Homebrew](https://formulae.brew.sh/formula/python@3.9),
I succeeded by creation of anautomation object
[as described here](https://stackoverflow.com/a/6445525/539470),
with following shell script to do it.

```
# Setup environment, I recommend you to have this file if you still do not
. $HOME/.bash_profile
# Now you can run your proper python3, in my case, /usr/local/bin/python3

# Run the script
$HOME/....my repo path..../pytraycharmap/run.sh 1>/dev/null 2>&1 &
# Output redirects and background are needed to tell
# the OS that it is safe to finish the script itself
```
