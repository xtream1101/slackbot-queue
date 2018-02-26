#!/bin/sh

IS_WORKER="${SB_WORKER:-true}"

echo $IS_WORKER

cd /src/

if $IS_WORKER; then
    echo "Run worker"
    celery -A slackbot worker --loglevel=info
else
    echo "Run listener"
    python3 -m slackbot.run_tasks
fi
