#!/bin/bash

set -eo pipefail

stderr() {
    echo "verify-server ┃ $*" 1>&2
}

run() {
    stderr "❯ $*"
    "$@"
}

run /opt/terminal-server/pyvenv/bin/python /opt/terminal-server/openai/server.py
