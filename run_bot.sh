#!/bin/bash

docker run \
  --name lmao \
  -v /home/earthling/lmaobot:/root/lmaobot \
  -e BOT_PROD='y' \
  --rm \
  lmaobot
