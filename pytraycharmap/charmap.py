#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tray char map. Simple context menu + clickless
multiple char selection with any key while hovered.
"""

import os
import sys
import yaml
from PyQt6 import QtGui, QtWidgets, QtCore

__author__ = 'Dmitry V. Luciv'
__license__ = 'WTFPL v2'
__version__ = '0.0.1.2'

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

class TypographyMenu(QtWidgets.QMenu):
    """
    Context menu of typographic symbols
    """

    def __init__(self, parent, app, menufilename):
        super().__init__(parent)

        # callback clear state
        self.clearcb = True

        # event filter to handle key press while hovering menu
        self.efilter = KeyEventFilter(self.actionKeyPressed)
        self.hoveredAction = None

        # fonts
        font = app.font()
        self.leaf_font = QtGui.QFont(font.family(), font.pointSize() + 2)

        # right now for right-handed users with tray in bottom-right
        self.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)

        # fill the menu
        self.addChars(menufilename)

        self.addSeparator()
 
        # clipboard & its handler
        # difficulties on Mac OS https://doc.qt.io/qt-6/qclipboard.html#dataChanged
        self.clip = app.clipboard()
        self.clip.dataChanged.connect(self.clipChanged)

        # clearcb action
        clearcbAction = self.addAction("Clear CB")
        clearcbAction.triggered.connect(self.clearcbClicked)

    def clipChanged(self):
        """
        Clipboard listener
        """
        # Is clipboard changed from outside? Ok, clean it next time.
        if type(self.sender()) != QtGui.QAction:
            self.clearcb = True

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
                    submenu.installEventFilter(self.efilter)
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
        self.clip.clear()
        self.clearcb = False

    def clipChar(self, c):
        """
        Adds character to clipboard or stores it, if clipboard was modified
        """
        self.clip.setText(
            ("" if self.clearcb else self.clip.text()) + c
        )
        self.clearcb = False

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
        # self.parent.show()
        # self.parent.setFocus()
        # self.parent.hide()

        # as context menu is needed for main purpose
        # if reason != QtWidgets.QSystemTrayIcon.ActivationReason.Context:
        #     self.showMessage("Event: " + str(reason), self.clip.text())

    def exitClicked(self):
        """
        Exit handler
        """
        self.hide()
        print("Bye!")
        sys.exit(0)

def go(menufilename):
    path = os.path.dirname(os.path.abspath(__file__))
    icon = QtGui.QIcon(os.path.join(path, "trayicon.svg"))

    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(icon)  # Envs with smart taskbars like Win10 and Mac OS

    # Not sure window is ever needed on all platforms
    w = QtWidgets.QMainWindow()
    w.hide()

    clippoard = app.clipboard()

    trayIcon = SystemTrayIcon(
        icon,
        w, # No window and None usually work ok too
        app,
        menufilename
    )

    trayIcon.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    print("This is not standalone tool, run as module")
