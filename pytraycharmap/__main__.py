#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

if __name__ == "__main__":
    # Solution from pip built-in package.
    # Allows to run as both directory and module with -m parameter
    # Considered bad, but used oftenly.
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import pytraycharmap.charmap

    if len(sys.argv) < 2:
        print("Menu file needed as argument")
        sys.exit(-1)

    app = pytraycharmap.charmap.TrayCharMapApp(sys.argv[1])
    sys.exit(app.exec())
