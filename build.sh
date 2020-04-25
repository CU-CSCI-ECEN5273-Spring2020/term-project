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
CLEANER="${PREFIX}-cleaner"

HOST="us.gcr.io"

docker build -t "local/${PREFIX}-${BASE}" ${BASE}/
docker build -t "${CONTROLLER}" controller/
docker build -t "${SPIDER}" spider/
docker build -t "${SCAN}" scanner/
docker build -t "${CLEANER}" cleaner/

if [ ! -z "${PROJECT}" ]; then
  docker tag "${CONTROLLER}" "${HOST}/${PROJECT}/${CONTROLLER}:${TAG}"
  docker tag "${SCAN}" "${HOST}/${PROJECT}/${SCAN}:${TAG}"
  docker tag "${SPIDER}" "${HOST}/${PROJECT}/${SPIDER}:${TAG}"
  docker tag "${CLEANER}" "${HOST}/${PROJECT}/${CLEANER}:${TAG}"

  docker push "${HOST}/${PROJECT}/${CONTROLLER}:${TAG}"
  docker push "${HOST}/${PROJECT}/${SCAN}:${TAG}"
  docker push "${HOST}/${PROJECT}/${SPIDER}:${TAG}"
  docker push "${HOST}/${PROJECT}/${CLEANER}:${TAG}"
fi
