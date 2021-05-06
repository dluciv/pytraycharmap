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
