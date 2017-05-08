#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tray char map. Simple context menu + clickless
multiple char selection with any key while hovered.
"""

import os
import sys
from PyQt5 import QtGui, QtWidgets, QtCore

__author__ = 'Dmitry V. Luciv'
__license__ = 'WTFPL v2'
__version__ = '0.0.0.2'

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

        if(event.type() == QtCore.QEvent.KeyPress):
            self.notifiable(event)

        return result

class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    """
    SysTray icon with context menu of typographic symbols.
    """

    def __init__(self, icon, parent, font, menufilename):
        super().__init__(icon, parent)

        # callback clear state
        self.clearcb = True

        # event filter to handle key press while hovering menu
        self.efilter = KeyEventFilter(self.actionKeyPressed)
        self.hoveredAction = None

        # font for menu leafs with letters
        self.font = QtGui.QFont(font.family(), 12)

        # right now for right-handed users with tray in bottom-right
        menu = QtWidgets.QMenu(parent)
        menu.setLayoutDirection(QtCore.Qt.RightToLeft)

        # fill the menu
        self.addChars(menu, menufilename)

        # exit action
        menu.addSeparator() # before exit
        exitAction = menu.addAction("Exit")
        exitAction.triggered.connect(self.exitClicked)

        # add context menu to icon
        self.setContextMenu(menu)

        # ballon on icon click
        self.activated.connect(self.iconClicked)

        # clipboard & its handler
        self.clip = QtWidgets.QApplication.clipboard()
        self.clip.dataChanged.connect(self.clipchanged)

    def clipchanged(self):
        """
        Clipboard listener
        """
        # Is clipboard changed from outside? Ok, clean it next time.
        if type(self.sender()) != QtWidgets.QAction:
            self.clearcb = True

    def addCharLeaf(self, menu, value):
        """
        Adds character item to menu
        """
        vaction = QtWidgets.QAction(value, menu, checkable=False)
        menu.addAction(vaction)
        vaction.setFont(self.font)

        vaction.triggered.connect(self.charTriggered)
        vaction.hovered.connect(self.charHovered)

    def processContents(self, menu, contents):
        """
        Recursively builds nested menus
        """
        if type(contents) == dict:
            for k in contents.keys():
                v = contents[k]
                submenu = QtWidgets.QMenu(" " + k, menu) # to keep space
                submenu.setLayoutDirection(QtCore.Qt.RightToLeft)
                menu.addMenu(submenu)
                self.processContents(submenu, v)
                submenu.installEventFilter(self.efilter)
        elif type(contents) == list:
            for e in contents:
                self.processContents(menu, e)
        elif type(contents) == str:
            self.addCharLeaf(menu, contents)
        else:
            print("WTF in menu?.. " + repr(contents), file=sys.stderr)

    def addChars(self, menu, menufilename):
        """
        Read menu file and build menu with it
        """
        import yaml

        with open(menufilename, encoding='utf-8') as yaf:
            try:
                contents = yaml.load(yaf)
                self.processContents(menu, contents)
            except Exception as e:
                print("Failed to load menu: " + repr(contents), file=sys.stderr)

    def iconClicked(self, reason):
        """
        SysTray icon clicking handler
        """
        # as context menu is needed for main purpose
        if reason != QtWidgets.QSystemTrayIcon.Context:
            self.showMessage("Event: " + str(reason), self.clip.text())

    def exitClicked(self):
        """
        Exit handler
        """
        self.hide()
        print("Bye!")
        sys.exit(0)

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
        self.clipChar(action.text())

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

def go(menufilename):
    app = QtWidgets.QApplication(sys.argv)
    w = QtWidgets.QMainWindow()

    path = os.path.dirname(os.path.abspath(__file__))
    trayIcon = SystemTrayIcon(QtGui.QIcon(os.path.join(path, "trayicon.svg")), w, app.font(), menufilename)

    trayIcon.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    print("This is not standalone tool")
