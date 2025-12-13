#!/bin/bash
JUPYTER_SERVER_OAI_PATH="${JUPYTER_SERVER_OAI_PATH:-"$HOME/.openai_internal"}"
JUPYTER_SERVER_LOG_CONFIG="${JUPYTER_SERVER_LOG_CONFIG:-"/home/sandbox/uvicorn_logging.config"}"
JUPYTER_SERVER_API_PORT="${JUPYTER_SERVER_API_PORT:-${API_PORT:-"8080"}}"
JUPYTER_SERVER_PYTHON="${JUPYTER_SERVER_PYTHON:-"python3"}"
ulimit -n 1048576
ulimit -v $PROCESS_MEMORY_LIMIT
cd $JUPYTER_SERVER_OAI_PATH || exit
if [ -f /usr/lib/x86_64-linux-gnu/libjemalloc.so.2 ]; then
    JEMALLOC_PATH=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2
elif [ -f /usr/lib/aarch64-linux-gnu/libjemalloc.so.2 ]; then
    JEMALLOC_PATH=/usr/lib/aarch64-linux-gnu/libjemalloc.so.2
else
    echo "libjemalloc not found"
    exit 1
fi
if [ ! -z "$JEMALLOC_PATH" ]; then
    echo "Using jemalloc at $JEMALLOC_PATH"
    export PYTHONMALLOC=malloc
    export MALLOC_CONF="narenas:1,background_thread:true,lg_tcache_max:10,dirty_decay_ms:5000,muzzy_decay_ms:5000"
    export LD_PRELOAD="$JEMALLOC_PATH"
fi
export PYDEVD_DISABLE_FILE_VALIDATION=1
exec tini -- "$JUPYTER_SERVER_PYTHON" -m uvicorn \
    --host 0.0.0.0 \
    --port "$JUPYTER_SERVER_API_PORT" \
    --log-config "$JUPYTER_SERVER_LOG_CONFIG" jupyter_server.app:app