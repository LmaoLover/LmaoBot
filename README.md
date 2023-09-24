# LmaoBot

Dank meme bot for Chatango

![LmaoBot](https://i.imgur.com/NAi47dM.png)

## How to Make Bot

### Use python >=3.8.1 and chatango-lib

Look at `requirements.txt` to get see what libraries you need.  The current bot is `async.py` and uses a modified version of chatango-lib: [LmaoLover/chatango-lib](https://github.com/LmaoLover/chatango-lib)

This library uses `asyncio` and has many advantages over the old version, but requires working in async style.

### About ch.py

The old version is `bot.py` which uses an updated version of ch.py: [TheClonerx/ch.py](https://github.com/TheClonerx/ch.py)

This library has issues with reconnecting when kicked from the chatango servers, and cannot handle messages in parallel.

### Python exceptions

Every error in python will crash your bot and you can't always tell what errors will happen.  Use try/except blocks to log errors instead of crashing.

```python
try:
  ...
except Exception as e:
  logError(room.name, "twitter", message.body, e)
```

### Infinite Bot

Your bot will still crash at some point so start your script in an infinite bash loop.

```bash
while true
do
    echo "Starting bot..."
    python3 /root/lmaobot/bot.py
    sleep 1
done
```

If your bot crashes too much then don't do this.

### Docker

If you use docker then you don't have to install python libraries manually on your system.

```bash
docker build -t lmaobot .

# Edit this script then run the bot
./run_bot.sh

# Stop or restart later
docker restart lmao
docker stop lmao
```

## LmaoBot Features

### MEMEs not included

You need to supply your own files like `lmao_memes.txt`.  They are loaded into the code and used like this: `memes['lmao']`

### config.yaml for connection info

```
username: UserName
password: mypassword
rooms:
    prod:
        - animechat
        - sportchat
    dev:
        - devchat
```

Use environment variable BOT_PROD to connect to real chat rooms.

```
BOT_PROD=1 python3 bot.py
```

### rooms.yaml for groups

You want to do different things in different chats so make groups in `rooms.yaml` then use in the code `chat['memers']`

```
memers:
    - coolchat
    - lmaochat
serious:
    - courtroomusa
mod:
    - lmaochat
```

### wolframalpha search

Using `??`.  Provide your api key in `wolfram.yaml`:

```
app_id: ...
```
