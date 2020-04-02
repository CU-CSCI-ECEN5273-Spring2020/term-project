#!/bin/bash

TAG="2020.4.2"
BASE="base"
PREFIX="term-project"
CONTROLLER="controller"
SCAN="scan"
WEB="web"

docker build -t "local/${PREFIX}-${BASE}"
docker build -t "${PREFIX}-${CONTROLLER}:${TAG}" ${CONTROLLER}/
docker build -t "${PREFIX}-${WEB}:${TAG}" ${WEB}/
docker build -t "${PREFIX}-${SCAN}:${TAG}" ${SCAN}/
