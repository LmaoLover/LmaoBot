FROM python:3.9-slim-bullseye

RUN pip install --upgrade pip setuptools

COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install -I html5lib

CMD ["/root/lmaobot/loop_bot.sh"]

