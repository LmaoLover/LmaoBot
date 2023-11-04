FROM python:3.10-slim-bookworm

ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/root/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install --upgrade pip setuptools

COPY requirements.txt .
RUN pip install -r requirements.txt

CMD ["/root/lmaobot/loop_bot.sh"]

