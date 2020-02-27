#!/bin/bash
# wait-for-postgres.sh

set -e

cmd="$@"
timer="2"

until runuser -l postgres -c 'pg_isready' 2>/dev/null; do
  >&2 echo "Postgres is unavailable - sleeping for $timer seconds"
  sleep $timer
done
>&2 echo "Postgres is READY"

