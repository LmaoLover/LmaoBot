# LmaoBot

Dank meme bot for Chatango

## How to Make Bot

### Use python3 and ch.py

Look at `Dockerfile` to get see what libraries you need.  We are using an updated version of ch.py: [TheClonerx/ch.py](https://github.com/TheClonerx/ch.py)

Even this version of ch.py has a crucial flaw which we have fixed using [a dank hack](https://github.com/LmaoLover/LmaoBot/commit/c3a5aa8a9dfe120f2320cbcec4a1cc6a6118ccb1).  There will be no PRs for this fix as it does not integrate with the useless features of ch.py.  We only care that `onMessage` is properly called for every message.  If your bot sometimes does not recognize a message it is probably due to this flaw and you should apply the hack. 

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

