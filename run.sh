#!/bin/sh

/usr/bin/env python3 $(dirname $0)/pytraycharmap $(dirname $0)/menu/charmap.yaml

# or so if it is in sys.path
# python3 -m pytraycharmap $(dirname $0)/menu/charmap.yaml
