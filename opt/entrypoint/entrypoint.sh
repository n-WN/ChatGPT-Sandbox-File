#!/bin/bash
# http://go/docs-link/cua-container-chrome-entrypoint

set -eu

stderr() {
    echo "entrypoint ┃ $*" 1>&2
}

run() {
    stderr "❯ $*"
    "$@"
}

unset OAI_SHARE_SLIDES_DIR
unset SLIDES_JS_DIR
unset TARBALLS_DIR

run exec supervisord -n -c /etc/supervisord.conf
