#!/usr/bin/env -S uv run --quiet --script --
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pyyaml",
#     "pyperclip",
# ]
# ///
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
F5     Same as Enter, but for the primary selection (X11/Wayland; see
       the note on pyperclip below).
Esc    Quit without copying.

Enter and F5 are only the defaults.  The keys can be changed with the
environment variables FZFCHARMAP_CLIPBOARD and FZFCHARMAP_PRIMARY, for
example:

    FZFCHARMAP_PRIMARY=ctrl-o ./run-fzf.sh

Space is deliberately not used, so that it can be typed in the search
query.

Clipboard access is handled by pyperclip.  On X11 and Wayland its
xclip/xsel/wl-clipboard backends also provide the primary selection;
Windows and macOS have no such concept, so there the primary-selection
key simply falls back to the clipboard.  The remaining third-party
dependency is PyYAML, for reading the menu.

The key bindings call back into this script instead of relying on a
POSIX shell, because fzf runs `--bind` commands with `cmd.exe` on
Windows and with `sh` elsewhere.  The script is therefore at home on
both Unix-like systems and Windows.

Requires fzf >= 0.37 (for `transform-border-label`).
"""

import inspect
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unicodedata

__author__ = 'Dmitry V. Luciv'
__license__ = 'WTFPL v2'
__version__ = '0.1.0'

DEFAULT_CLIPBOARD_KEY = 'enter'
DEFAULT_PRIMARY_KEY = 'f5'

# Internal sub-command used from the fzf key binding.
APPEND_COMMAND = '--append'


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


def quote_argument(value):
    """
    Quote a single argument for the shell fzf uses to run `--bind`
    commands: `cmd.exe` on Windows, POSIX `sh` (or whatever $SHELL
    points at) everywhere else.
    """
    if os.name == 'nt':
        # Double quotes keep spaces and, more importantly, characters
        # like & and ( that cmd.exe would otherwise treat specially.
        # Forward slashes are understood both by cmd.exe and by the
        # POSIX shells (Git Bash, Cygwin) that fzf may pick up on
        # Windows when $SHELL is set.
        return '"%s"' % value.replace('\\', '/')
    return shlex.quote(value)


def self_command(*args):
    """
    Command line that re-invokes this very script with the given
    arguments.  A literal `{}` placeholder may be appended by the
    caller: fzf quotes it itself for the active shell.
    """
    parts = [sys.executable or 'python', os.path.abspath(__file__)]
    parts.extend(args)
    return ' '.join(quote_argument(part) for part in parts)


def build_fzf_command(clipboard_key, primary_key):
    """
    fzf invocation with our key bindings.

    The growing string is shown in the border label, so the input line
    stays free for the search query.
    """
    # Tab is handled entirely inside this script: the {} placeholder
    # carries the whole selected line over and fzf takes care of quoting
    # it for cmd.exe on Windows or for sh elsewhere.  Appending the
    # character and refreshing the border label happen in one process.
    # {1} is deliberately not used, because fzf trims whitespace off
    # single fields and would eat characters like NBSP.
    tab_binding = 'tab:transform-border-label(%s {})' % self_command(APPEND_COMMAND)
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


def append_and_label(line):
    """
    fzf key binding helper.

    `line` is the highlighted entry ("character<TAB>display").  Append
    the character to the growing string kept in $FZFCHAR_BUF and print
    the updated border label.  Doing both here keeps the number of
    spawned processes at one per key press.
    """
    buffer_path = os.environ.get('FZFCHAR_BUF', '')
    value = line.split('\t', 1)[0]
    if value and buffer_path:
        with open(buffer_path, 'a', encoding='utf-8') as buff:
            buff.write(value)

    growing = ''
    if buffer_path:
        try:
            with open(buffer_path, encoding='utf-8') as buff:
                growing = buff.read()
        except OSError:
            pass

    # fzf expects the label in UTF-8, which the console encoding is not
    # necessarily, so write the bytes ourselves.
    sys.stdout.buffer.write(('chars: %s' % growing).encode('utf-8'))
    return 0


def copy_text(text, primary=False):
    """
    Put `text` into the clipboard via pyperclip.

    When `primary` is true and the detected backend offers a primary
    selection, the text goes there instead.  Only the xclip/xsel/
    wl-clipboard backends used on X11 and Wayland do; the Windows,
    macOS, Qt and Klipper backends fall back to the clipboard.
    """
    try:
        import pyperclip
    except ImportError:  # pragma: no cover
        sys.stderr.write(
            "pyperclip is required for clipboard access.\n"
            "Install it with: pip3 install --user pyperclip\n"
        )
        return 1

    copy = pyperclip.determine_clipboard()[0]
    if primary and 'primary' in inspect.signature(copy).parameters:
        copy(text, primary=True)
    else:
        copy(text)
    return 0


def run(menufile):
    try:
        import yaml
    except ImportError:  # pragma: no cover
        sys.stderr.write(
            "PyYAML is required to read the menu file.\n"
            "Install it with: pip3 install --user pyyaml\n"
        )
        return 1

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

    try:
        return copy_text(text, primary=(key == primary_key))
    except (OSError, RuntimeError) as exc:
        sys.stderr.write("Could not copy the text: %s\n" % exc)
        return 1


def main(argv):
    if len(argv) > 1 and argv[1] == APPEND_COMMAND:
        return append_and_label(argv[2] if len(argv) > 2 else '')

    here = os.path.dirname(os.path.abspath(__file__))
    menufile = argv[1] if len(argv) > 1 else os.path.join(here, 'menu', 'charmap.yaml')
    return run(menufile)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
