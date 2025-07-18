#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tray char map. Simple context menu + clickless
multiple char selection with any key while hovered.
"""

import os
import sys
import subprocess
import yaml
from abc import ABC, abstractmethod
from PyQt6 import QtGui, QtWidgets, QtCore
from PyQt6.QtCore import QThread

__author__ = 'Dmitry V. Luciv'
__license__ = 'WTFPL v2'
__version__ = '0.8.0'

class KeyEventFilter(QtCore.QObject):
    def __init__(self, notifiable):
        super().__init__()
        self.notifiable = notifiable

    def eventFilter(self, receiver, event):
        # Typically, filter chould call super after check,
        # and put its logic before.
        # This one can also work so without changes,
        # but lets be as graceful as possible.
        result = super(KeyEventFilter, self).eventFilter(receiver, event)

        if(event.type() == QtCore.QEvent.Type.KeyPress):
            self.notifiable(event)

        return result

class MouseEventFilter(QtCore.QObject):
    """
    Not working yet...
    """
    def __init__(self, notifiable):
        super().__init__()
        self.notifiable = notifiable

    def eventFilter(self, receiver, event):
        result = super(MouseEventFilter, self).eventFilter(receiver, event)

        # print(self, receiver, event)

        if event.type() == QtCore.QEvent.Type.MouseButtonPress:
            if event.button() == QtCore.Qt.MouseButtons.LeftButton:
                print("Left button clicked")
            elif event.button() == QtCore.Qt.MouseButtons.RightButton:
                print("Right button clicked")

        return result

class TypographyMenu(QtWidgets.QMenu):
    """
    Context menu of typographic symbols
    """

    def __init__(self, parent, app, menufilename):
        super().__init__(parent)

        # event filter to handle presses while hovering menu
        self.kefilter = KeyEventFilter(self.actionKeyPressed)
        self.mefilter = MouseEventFilter(self.mouseButtonPressed)

        self.hoveredAction = None

        # fonts
        font = app.font()
        self.leaf_font = QtGui.QFont(font.family(), font.pointSize() + 2)

        # right now for right-handed users with tray in bottom-right
        self.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)

        # fill the menu
        self.addChars(menufilename)

        self.addSeparator()

        self.app = app

        # clearcb action
        clearcbAction = self.addAction("Clear CB")
        clearcbAction.triggered.connect(self.clearcbClicked)

    def addCharLeaf(self, menu, value, menuitem_note=None):
        """
        Adds character item to menu
        """
        menuitem_text = f"{menuitem_note}: [{value}]" if menuitem_note else value
        vaction = QtGui.QAction(menuitem_text, menu, checkable=False)
        vaction.setData(value)
        menu.addAction(vaction)
        vaction.setFont(self.leaf_font)

        vaction.triggered.connect(self.charTriggered)
        vaction.hovered.connect(self.charHovered)

    def processContents(self, menu, contents):
        """
        Recursively builds nested menus
        """
        if isinstance(contents, dict):
            contents_items = list(contents.items())
            if len(contents_items) == 1 and type(contents_items[0][1]) == str:  # Single char with comment
                note, value = contents_items[0]
                self.addCharLeaf(menu, value, note)
            else:  # Submenu
                for k, v in contents_items:
                    submenu = QtWidgets.QMenu(" " + k, self) # to keep space
                    submenu.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
                    menu.addMenu(submenu)
                    self.processContents(submenu, v)
                    submenu.installEventFilter(self.kefilter)
                    submenu.installEventFilter(self.mefilter)
        elif isinstance(contents, list):
            for e in contents:
                self.processContents(menu, e)
        elif isinstance(contents, str):
            self.addCharLeaf(menu, contents)
        else:
            print("WTF in menu?.. " + repr(contents), file=sys.stderr)

    def addChars(self, menufilename):
        """
        Read menu file and build menu with it
        """
        with open(menufilename, encoding='utf-8') as yaf:
            try:
                contents = yaml.load(yaf, Loader=yaml.FullLoader)
                self.processContents(self, contents)
            except Exception as e:
                print("Failed to initialize menu: " + repr(e), file=sys.stderr)

    def clearcbClicked(self):
        self.app.backend1.clear_input()

    def clipChar(self, c):
        """
        Adds character to clipboard or stores it, if clipboard was modified
        """
        self.app.backend1.input_str(c)

    def charTriggered(self):
        """
        Action handler for character click
        """
        action = self.sender()
        self.clipChar(action.data())

    def charHovered(self):
        """
        Action handler for character hover
        """
        self.hoveredAction = self.sender()

    def actionKeyPressed(self, event):
        """
        Called by key listener instance above
        """
        if self.hoveredAction:
            self.hoveredAction.trigger()

    def mouseButtonPressed(self, event):
        """
        Called by key listener instance above
        """
        if self.hoveredAction:
            self.hoveredAction.trigger()


class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    """
    SysTray icon with context menu of typographic symbols.
    """

    def __init__(self, icon, parent, app, menufilename):
        super().__init__(icon)

        self.parent = parent

        # callback clear state
        self.clearcb = True

        # right now for right-handed users with tray in bottom-right
        menu = TypographyMenu(parent, app, menufilename)

        # exit action
        exitAction = menu.addAction("Exit")
        exitAction.triggered.connect(self.exitClicked)

        # add context menu to icon
        self.setContextMenu(menu)

        # ballon on icon click
        self.activated.connect(self.iconClicked)

    def iconClicked(self, reason):
        """
        SysTray icon clicking handler
        """
        pass

    def exitClicked(self):
        """
        Exit handler
        """
        self.hide()
        print("Bye!")
        sys.exit(0)


class InputBackend(ABC):
    @abstractmethod
    def input_str(self, c: str) -> None:
        ...

    @abstractmethod
    def clear_input(self) -> None:
        ...

class ClipboardBackend(InputBackend):
    def __init__(self, clipboard):
        super().__init__()
        self.clipboard = clipboard
        self.clipvalue = ""

    def clear_input(self)-> None:
        self.clipboard.setText("")
        self.clipvalue = ""

    def input_str(self, c: str)-> None:
        # On Mac OS we can't monitor clipboard with
        # self.clipboard.dataChanged.connect(...handler...)
        # https://doc.qt.io/qt-6/qclipboard.html#dataChanged

        if self.clipboard.text() == self.clipvalue:  # no outside modifications
            self.clipvalue += c
        else:  # clipboard modified by another app
            self.clipvalue = c
        self.clipboard.setText(self.clipvalue)


class CCCPBackend(InputBackend):
    def __init__(self, use_primary: bool):
        super().__init__()
        self._use_primary = use_primary
        self._buffer_bytes = b''

    def _get_buffer(self)-> str:
        cccp = subprocess.run(
            ['cccp'] + (['--primary'] if self._use_primary else []) + ['p'],
            capture_output=True #, check=True
        )
        return cccp.stdout

    def clear_input(self)-> None:
        subprocess.run(
            ['cccp'] + (['--primary'] if self._use_primary else []) + ['c'],
            input=b'' #, check=True
        )

    def input_str(self, c: str)-> None:
        b = c.encode('utf-8')

        if self._get_buffer() == self._buffer_bytes:  # no outside modifications
            subprocess.run(
                ['cccp'] + (['--primary'] if self._use_primary else []) + ['--append', 'c'],
                input=b #, check=True
            )
            self._buffer_bytes += b
        else:  # clipboard modified by another app
            subprocess.run(
                ['cccp'] + (['--primary'] if self._use_primary else []) + ['c'],
                input=b #, check=True
            )
            self._buffer_bytes = b

class WTypeBackend(InputBackend):
    """
    wtype backend for Wayland, usually wlroots
    """
    class TypingThread(QThread):
        def __init__(self, key: str):
            super().__init__()
            self.key = key

        def run(self):
            result = subprocess.run(["wtype", "-s", "100", self.key], capture_output=True, text=True)
            if result.returncode != 0:
                print(result.stdout)
                print(result.stderr, file=sys.stderr)

    def __init__(self):
        super().__init__()

    def input_str(self, c: str) -> None:
        WTypeBackend.TypingThread(c).run()

    def clear_input(self)-> None:
        print("Input clear is not supported for wtype backend", file=sys.stderr)

class TrayCharMapApp(QtWidgets.QApplication):
    def detect_backend(self) -> None:
        if len(sys.argv) > 2:
            if sys.argv[2] == 'cccp-p':
                return CCCPBackend(True)
            elif sys.argv[2] == 'cccp-c':
                return CCCPBackend(False)

        xdg_current_desktop = os.environ.get('XDG_CURRENT_DESKTOP')
        if xdg_current_desktop == 'sway' or xdg_current_desktop == 'wlroots':
            result = subprocess.run(["which", "wtype"], capture_output=True)
            if result.returncode == 0:
                return WTypeBackend()

        return ClipboardBackend(self.clipboard())

    def __init__(self, menufilename: str) -> None:
        super().__init__(sys.argv)
        self.menufilename = menufilename
        self.initUI()

        self.backend1 = self.detect_backend()
        self.backend2 = self.backend1 \
            if isinstance(self.backend1, ClipboardBackend) \
            else ClipboardBackend(self.clipboard())

    def initUI(self)-> None:
        path = os.path.dirname(os.path.abspath(__file__))
        icon = QtGui.QIcon(os.path.join(path, "trayicon.svg"))

        self.setWindowIcon(icon)  # Envs with smart taskbars like Win10 and Mac OS

        self.trayIcon = SystemTrayIcon(
            icon,
            None, # w, # No window and None usually work ok too
            self,
            self.menufilename
        )

        self.trayIcon.show()

    def exec(self)-> object:
        return super().exec()


if __name__ == '__main__':
    print("This is not standalone tool, run as module")
