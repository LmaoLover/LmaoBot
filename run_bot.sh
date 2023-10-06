#!/bin/bash

docker run \
  --name lmao \
  -v /home/earthling/LmaoBot:/root/lmaobot \
  -e BOT_PROD='y' \
  -e OPENAI_API_KEY='...' \
  -e KEKG_URL='...' \
  --rm \
  lmaobot
