#!/bin/bash

helpFunction() {
  echo "Usage: $0 <project>" >&2
  echo -e "\tproject - A project organizes all your Google Cloud resources" >&2
  exit 1
}
if [ $# -eq 0 ]; then
  PROJECT=""
elif [ $# -eq 1 ]; then
  PROJECT="$1"
else
  helpFunction
fi

YEAR=$(date +%Y)
MONTH=$(date +%m)
DAY=$(date +%d)

TAG="${YEAR}.${MONTH}.${DAY}"
BASE="base"
PREFIX="term-project"
CONTROLLER="${PREFIX}-controller"
SCAN="${PREFIX}-scanner"
SPIDER="${PREFIX}-spider"

docker build -t "${CONTROLLER}"
docker build -t "${SPIDER}"
docker build -t "${SCAN}"

