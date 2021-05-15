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

class TypographyMenu(QtWidgets.QMenu):
    """
    Context menu of typographic symbols
    """

    def __init__(self, parent, app, menufilename):
        super().__init__(parent)

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
        self.app.clearCB()

    def clipChar(self, c):
        """
        Adds character to clipboard or stores it, if clipboard was modified
        """
        self.app.clipChar(c)

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

    def exitClicked(self):
        """
        Exit handler
        """
        self.hide()
        print("Bye!")
        sys.exit(0)


class TrayCharMapApp(QtWidgets.QApplication):
    def __init__(self, menufilename: str) -> None:
        super().__init__(sys.argv)
        self.menufilename = menufilename
        self.initUI()
        self.clippoard = self.clipboard()
        self.clipvalue = ""

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
    
    def clearCB(self)-> None:
        self.clippoard.setText("")
        self.clipvalue = ""
    
    def clipChar(self, c: str)-> None:
        # On Mac OS we can't monitor clipboard with
        # self.clipboard.dataChanged.connect(...handler...)
        # https://doc.qt.io/qt-6/qclipboard.html#dataChanged

        if self.clippoard.text() == self.clipvalue:  # no outside modifications
            self.clipvalue += c
        else:  # clipboard modified by another app
            self.clipvalue = c
        self.clippoard.setText(self.clipvalue)

    def exec(self)-> object:
        return super().exec()


if __name__ == '__main__':
    print("This is not standalone tool, run as module")
