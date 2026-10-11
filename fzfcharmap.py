#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
fzf-based frontend for PyTrayCharMap.

It reads the very same menu file as the tray version (menu/charmap.yaml)
and shows all characters as a searchable list in fzf.

Keys
----
Tab    Append the highlighted character to the growing string.  The
       string is shown in the border label, so the input line stays
       free for the search query.
Enter  Copy the growing string to the clipboard.  When the string is
       still empty, the highlighted character is copied instead.
F5     Same as Enter, but for the primary selection.
Esc    Quit without copying.

Enter and F5 are only the defaults.  The keys can be changed with the
environment variables FZFCHARMAP_CLIPBOARD and FZFCHARMAP_PRIMARY, for
example:

    FZFCHARMAP_PRIMARY=ctrl-o ./run-fzf.sh

Space is deliberately not used, so that it can be typed in the search
query.

Clipboard and primary selection access is delegated to the `cccp`
script, so the only third-party dependency here is PyYAML (for reading
the menu) and, of course, fzf itself.

Requires fzf >= 0.37 (for `transform-border-label`).
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "PyYAML is required to read the menu file.\n"
        "Install it with: pip3 install --user pyyaml\n"
    )
    sys.exit(1)

__author__ = 'Dmitry V. Luciv'
__license__ = 'WTFPL v2'
__version__ = '0.1.0'

DEFAULT_CLIPBOARD_KEY = 'enter'
DEFAULT_PRIMARY_KEY = 'f5'


def fallback_description(value):
    """
    Build a searchable description from the Unicode name, used when
    the menu file does not provide one.
    """
    if not value:
        return ''
    try:
        name = unicodedata.name(value[0])
    except ValueError:
        return 'U+%04X' % ord(value[0])
    words = name.title().split()
    return ' '.join(w for w in words if w.lower() != 'letter')


def iter_leaves(node, path=()):
    """
    Walk the parsed menu and yield (value, description, path) tuples.

    The menu format is the one understood by the Qt version: a one-item
    mapping whose value is a string is a described character, any other
    mapping is a submenu, lists are flat groups and bare strings are
    characters without a description.
    """
    if isinstance(node, dict):
        items = list(node.items())
        if len(items) == 1 and isinstance(items[0][1], str):
            description, value = items[0]
            yield value, description, path
        else:
            for key, child in items:
                yield from iter_leaves(child, path + (str(key),))
    elif isinstance(node, list):
        for child in node:
            yield from iter_leaves(child, path)
    elif isinstance(node, str):
        yield node, '', path


def build_menu_lines(contents):
    """
    Turn the parsed menu into fzf input.

    Every line has two tab-separated fields:
      1) the raw character (what the Tab binding collects and what the
         wrapper extracts after fzf exits)
      2) the human readable text actually shown by fzf
    """
    lines = []
    for value, description, path in iter_leaves(contents):
        if not description:
            description = fallback_description(value)
        display = '%s   %s' % (value, description)
        if path:
            display += '   \x1b[90m%s\x1b[0m' % '/'.join(path)
        lines.append('%s\t%s' % (value, display))
    return '\n'.join(lines) + ('\n' if lines else '')


def pretty_key(key):
    """
    Turn an fzf key name into something nice for the header line.
    """
    if key.startswith('f') and key[1:].isdigit():
        return key.upper()
    if key.startswith('ctrl-'):
        return 'Ctrl-' + key[5:].upper()
    return key.capitalize()


def build_fzf_command(clipboard_key, primary_key):
    """
    fzf invocation with our key bindings.

    The growing string is shown in the border label, so the input line
    stays free for the search query.
    """
    tab_binding = (
        # {1} would mangle characters like NBSP, so take the whole line
        # and cut the display field off at the first tab.
        'tab:execute-silent(c={}; printf %s "${c%%\t*}" >> "$FZFCHAR_BUF")'
        '+transform-border-label(printf "chars: %s" "$(cat "$FZFCHAR_BUF")")'
    )
    header = 'Tab: append    %s: clipboard    %s: primary    Esc: quit' % (
        pretty_key(clipboard_key), pretty_key(primary_key))
    return [
        'fzf',
        '--delimiter=\t',
        '--with-nth=2',        # show the pretty field
        '--expect=%s,%s' % (clipboard_key, primary_key),
        '--ansi',
        '--border=rounded',
        '--border-label=chars: ',
        '--prompt=> ',
        '--header=' + header,
        '--bind=' + tab_binding,
    ]


def cccp_copy(text, primary):
    """
    Put `text` into the clipboard (or primary selection) via cccp.
    """
    if shutil.which('cccp') is None:
        sys.stderr.write("cccp not found in PATH\n")
        return 1
    command = ['cccp'] + (['--primary'] if primary else []) + ['c']
    return subprocess.run(command, input=text.encode('utf-8')).returncode


def run(menufile):
    with open(menufile, encoding='utf-8') as menuf:
        contents = yaml.safe_load(menuf)

    menu_data = build_menu_lines(contents)
    if not menu_data.strip():
        sys.stderr.write("Menu file '%s' has no characters\n" % menufile)
        return 1

    if shutil.which('fzf') is None:
        sys.stderr.write("fzf not found in PATH\n")
        return 1

    clipboard_key = os.environ.get('FZFCHARMAP_CLIPBOARD', DEFAULT_CLIPBOARD_KEY)
    primary_key = os.environ.get('FZFCHARMAP_PRIMARY', DEFAULT_PRIMARY_KEY)

    # The Tab binding appends characters to this file, the wrapper reads
    # it back once fzf is done with the growing string.
    buffer_file = tempfile.NamedTemporaryFile(prefix='fzfcharmap.', delete=False)
    buffer_file.close()

    env = dict(os.environ, FZFCHAR_BUF=buffer_file.name)
    try:
        completed = subprocess.run(
            build_fzf_command(clipboard_key, primary_key),
            input=menu_data.encode('utf-8'),
            stdout=subprocess.PIPE,
            env=env,
        )
        output = completed.stdout.decode('utf-8', 'replace')
        with open(buffer_file.name, encoding='utf-8') as buff:
            growing = buff.read()
    finally:
        try:
            os.unlink(buffer_file.name)
        except OSError:
            pass

    lines = output.split('\n')
    key = lines[0] if lines else ''
    # The selected line looks like "char<TAB>display"; keep the char only.
    accepted = lines[1].split('\t', 1)[0] if len(lines) > 1 else ''

    # Anything but the copy keys means the user aborted: do not copy.
    if key not in (clipboard_key, primary_key):
        return 0

    text = growing if growing else accepted
    if not text:
        return 0

    return cccp_copy(text, primary=(key == primary_key))


def main(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    menufile = argv[1] if len(argv) > 1 else os.path.join(here, 'menu', 'charmap.yaml')
    return run(menufile)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
