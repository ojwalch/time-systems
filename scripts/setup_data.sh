#!/usr/bin/env bash
# Fetch the two pinned datasets and compile the tz data. Run from the repo root.
#   IANA tz database (clock history, incl. pre-1970 'backzone' detail)
#   World Bank total population (via github.com/datasets/population)
set -euo pipefail
TZ_COMMIT=$(cat data/tz_commit.txt)
POP_COMMIT=$(cat data/population_commit.txt)

mkdir -p vendor-src
if [ ! -d vendor-src/tz ]; then
  git clone https://github.com/eggert/tz vendor-src/tz
fi
git -C vendor-src/tz fetch --depth 1 origin "$TZ_COMMIT" 2>/dev/null || true
git -C vendor-src/tz checkout -q "$TZ_COMMIT"

if [ ! -d vendor-src/population ]; then
  git clone https://github.com/datasets/population vendor-src/population
fi
git -C vendor-src/population fetch --depth 1 origin "$POP_COMMIT" 2>/dev/null || true
git -C vendor-src/population checkout -q "$POP_COMMIT"

# Compile with the system zic (reads the tz source files as data only).
rm -rf build/zoneinfo && mkdir -p build/zoneinfo
zic -b fat -d build/zoneinfo vendor-src/tz/{africa,antarctica,asia,australasia,europe,northamerica,southamerica,etcetera,backzone}
echo "Data ready: tz $TZ_COMMIT, population $POP_COMMIT"
