#!/bin/sh

IS_WORKER="${SB_WORKER:-true}"

echo $IS_WORKER

cd /src/

if $IS_WORKER; then
    celery -A slackbot worker --loglevel=info -Ofair
else
    python3 -m slackbot.run_tasks
fi
