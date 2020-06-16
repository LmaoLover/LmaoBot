# LmaoBot

Dank meme bot for Chatango

![LmaoBot](https://i.imgur.com/NAi47dM.png)

## How to Make Bot

### Use python3 and ch.py

Look at `Dockerfile` to get see what libraries you need.  We are using an updated version of ch.py: [TheClonerx/ch.py](https://github.com/TheClonerx/ch.py)

Even this version of ch.py has a crucial flaw which we have fixed using [a dank hack](https://github.com/LmaoLover/LmaoBot/commit/c3a5aa8a9dfe120f2320cbcec4a1cc6a6118ccb1).  There will be no PRs for this fix as it does not integrate with the useless features of ch.py.  We only care that `onMessage` is properly called for every message.  If your bot sometimes does not recognize a message it is probably due to this flaw and you should apply the hack. 

### Python exceptions

Every error in python will crash your bot and you can't always tell what errors will happen.  Use try/except blocks to log errors instead of crashing.

```python
try:
  ...
except Exception as e:
  logError(room.name, "twitter", message.body, e)
```

### Chatango will disconnect you

Eventually chatango will just disconnect you from rooms, and usually once this begins it will gradually disconnect you from all rooms over the course of 2-3 minutes.  Reconnecting the room right away doesn't work using ch.py, so just let bot be dead for a couple minutes and restart the whole thing.

```python
def onDisconnect(self, room):
    # tell ch.py to wait a few minutes then stop
    self.setTimeout(169, self.stop)
```

```python
# Start your bot inside infinite loop
while True:
  ...
  bot.main()
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

If your bot crashes a lot then get it together first.

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

### twitter.yaml for the twitter gods

Tweet text is no longer delivered via HTTP so you need to use the cringe Twitter API.  Create a developer app and put the credentials into `twitter.yaml`:

```
consumer_key: ...
consumer_secret: ...
access_token_key: ...
access_token_secret: ...
```
