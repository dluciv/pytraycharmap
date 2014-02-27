#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

if __name__ == "__main__":
    # Solution from pip built-in package.
    # allows to run as both directory and moule with -m parameter
    # Considered bad, but used oftenly.
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import pytraycharmap.charmap

    if len(sys.argv) < 2:
        print("Menu file needed as argument")
        sys.exit(-1)

    pytraycharmap.charmap.go(sys.argv[1])
