FROM alpine:3.14

RUN apk update
RUN apk add python3 g++ gcc python3-dev py3-pip py3-lxml
RUN pip3 install --upgrade pip setuptools
RUN pip3 install requests pytz lassie pyyaml python-twitter youtube-search wolframalpha

CMD ["/root/lmaobot/loop_bot.sh"]

