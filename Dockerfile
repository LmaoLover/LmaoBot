FROM alpine:3.10

RUN apk update
RUN apk add python3 g++ gcc python3-dev libxml2-dev libxslt-dev
RUN pip3 install --upgrade pip setuptools
RUN pip3 install requests pytz lassie lxml pyyaml
RUN pip3 install python-twitter
RUN pip3 install youtube-search
RUN pip3 install wolframalpha

CMD ["/root/lmaobot/loop_bot.sh"]

