#!/bin/sh

exec "$(dirname "$0")/fzfcharmap.py" "$(dirname "$0")/menu/charmap.yaml" "$@"
