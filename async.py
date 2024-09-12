import os
import re
import json
import yaml
import random
import requests
import asyncio
import chatango
import logging
import logging.config
from bs4 import BeautifulSoup, Tag
from pytz import timezone
from calendar import timegm
from datetime import datetime, timedelta
from time import gmtime
from youtube_search import YoutubeSearch
from urllib.parse import urlparse, urlunparse, parse_qs
from wolframalpha import Client
from collections import deque
from asyncio import to_thread
from dotenv import load_dotenv

load_dotenv()
import anthropic
import kekg
import kodi
import brave
from imdb import imdb_info_by_id, imdb_info_by_search, imdb_printout


class LowercaseFormatter(logging.Formatter):
    def format(self, record):
        record.levelname = record.levelname.lower()
        return logging.Formatter.format(self, record)


logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"()": LowercaseFormatter, "format": "[%(levelname)s] %(message)s"},
    },
    "handlers": {
        "default": {
            "level": "DEBUG",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

logging.config.dictConfig(logging_config)

cwd = os.path.dirname(os.path.abspath(__file__))


def random_selection(list):
    return list[random.randint(0, len(list) - 1)]


def log(room_name, sub, message):
    if sub:
        filename = "{0}_{1}.log".format(room_name, sub)
    else:
        filename = "{0}.log".format(room_name)

    time_str = "{:%Y-%m-%d %H:%M:%S}".format(datetime.now(timezone("America/Denver")))

    with open(cwd + "/logs/" + filename, "a") as logfile:
        logfile.write("[{0}] {1}\n".format(time_str, message))


def logError(room_name, sub, message_body, e):
    log("errors", None, "[{}] [{}] {}".format(room_name, sub, message_body))
    log("errors", None, "[{}] [{}] {}".format(room_name, sub, repr(e)))


memes = {}
for filename in os.listdir(cwd):
    if filename[-10:] == "_memes.txt":
        meme_type = filename[:-10]
        memes[meme_type] = [line.rstrip("\n") for line in open(cwd + "/" + filename)]

with open(cwd + "/rooms.yaml", "r") as roomsyaml:
    chat = yaml.safe_load(roomsyaml)

with open(cwd + "/wolfram.yaml", "r") as wolframyaml:
    keys = yaml.safe_load(wolframyaml)
    wolfram_client = Client(keys["app_id"])

with open(cwd + "/stash_memes.json", "r") as stashjson:
    stash_memes = json.load(stashjson)

stash_tuples = [(k, v) for k, v in stash_memes.items()]

link_re = re.compile(r"https?://\S+")
yt_re = re.compile(
    r"(?:youtube(?:-nocookie)?\.com/(?:[^/]+/.+/|(?:v|e(?:mbed)?)/|.*[?&]v=)|youtu\.be/|shorts/)([a-zA-Z0-9_-]{11})"
)
imdb_re = re.compile(r"(?:.*\.|.*)imdb.com/(?:t|T)itle(?:\?|/)(..\d+)")
twitter_re = re.compile(r"(twitter|x).com/[a-zA-Z0-9_]+/status/([0-9]+)", re.IGNORECASE)
clean_tag_re = re.compile("<.*?>")


def room_history(room, max_messages: int = 20) -> list[chatango.Message]:
    return [
        msg
        for msg in list(reversed(room.history))[:max_messages]
        if chatango.MessageFlags.CHANNEL_MOD not in msg.flags
        and "WWWWWW" not in msg.body
    ]


def render_history(history, max_length=999):
    listory = [
        "{}: {}\n".format(msg.user.name, msg.body[:max_length]) for msg in (history)
    ]

    tot_len = 0
    for i, line in enumerate(listory):
        tot_len += len(line)
        if tot_len > 2900:
            listory = listory[: i + 1]

    return "".join(reversed(listory))


roger_messages = [
    "sup",
    "hey girl",
    "ayyyy",
    "Let's get this bread",
    "What you need?",
    "Yo waddup",
]

simple_memes: dict[str, str] = {
    "!whatson": "https://guide.lmao.love/",
    "!jameis": stash_memes["/jameis"],
    "!winston": stash_memes["/jameis"],
    "!phins": stash_memes["/phins"],
    "!spike": stash_memes["/1smoke"],
    "pika": stash_memes["/pikaa"],
    "devil?": stash_memes["/devil?"],
    "go2bed": stash_memes["/go2bed"],
    "gil2bed": stash_memes["/gil2bed"],
}

random_memes: dict[str, list[str]] = {
    "lmao?": roger_messages,
    "clam": memes["clam"],
    "lmoa": memes["lmoa"],
    "maga": memes["trump"],
    "biden": memes["biden"],
    "tyson": memes["tyson"],
    "propaganda": memes["korea"],
    "xmas": memes["santa"],
    "christmas": memes["santa"],
    "shkreli": memes["shkreli"],
    "jumanji": memes["jumanji"],
    "ronaldo": memes["ronaldo"],
    "rolando": memes["ronaldo"],
    "penaldo": memes["ronaldo"],
    "dance": memes["dance"],
    "!wo": memes["wo"],
    "henlo": ["BAZOO!!!", "HOOOOOOOOOO"],
}

kekg_actions = {
    "!moviespam": (kekg.movies, {"spam": True}),
    "!moviesspam": (kekg.movies, {"spam": True}),
    "!imdbspam": (kekg.movies, {"spam": True, "imdb": True}),
    "!movies": (kekg.movies, {}),
    "!sports": (kekg.sports, {}),
    "!egg": (kekg.egg, {}),
    "!march": (kekg.march, {}),
    "!showspam": (kekg.shows, {"spam": True}),
    "!showsspam": (kekg.shows, {"spam": True}),
    "!shows": (kekg.shows, {}),
    "!moviesalt": (kekg.movies_alt, {}),
    "!sportsalt": (kekg.sports_alt, {}),
    "!church": (kekg.church, {}),
    "!reality": (kekg.reality, {}),
    "!p": (kodi.progress, {}),
}

kodi_actions = {
    "!pixel": (kodi.pixel_toggle, {}),
}

meme_cmds = "|".join(
    re.escape(cmd) for cmd in list(simple_memes.keys()) + list(random_memes.keys())
)
command_re = re.compile(r"\/[^\s]*|stash|ay+ lmao|" + meme_cmds, flags=re.IGNORECASE)


class LmaoRoom(chatango.Room):
    def __init__(self, name: str):
        super().__init__(name)
        self.last_msg_time = 0
        self.send_queue = asyncio.Queue()
        # Hack a smaller history size
        self._history = deque(maxlen=50)

        self.add_task(self._process_send_queue())

    async def send_message(self, message, **kwargs):
        msg = message[: self._maxlen * 3]

        delay_time = kwargs.pop("delay", None)
        if delay_time:
            self.add_delayed_task(delay_time, self.send_message(message, **kwargs))
            return

        await self.send_queue.put((msg, kwargs))

    async def _process_send_queue(self):
        while True:
            msg, kwargs = await self.send_queue.get()
            previous_msg_time = self.last_msg_time
            current_msg_time = timegm(gmtime())
            time_since_last_msg = current_msg_time - previous_msg_time

            if self.rate_limit and time_since_last_msg < self.rate_limit:
                wait_time = self.rate_limit + 1 - time_since_last_msg
                await asyncio.sleep(wait_time)

            self.last_msg_time = timegm(gmtime())
            await super().send_message(msg, **kwargs)


class LmaoPM(chatango.PM):
    pass


class LmaoBot(chatango.Client):
    async def praise_jesus(self, room):
        jesus_message = random_selection(
            [
                "Thank You Based Jesus",
                "Praise him",
                "Lost sheep return to me",
                "Praise in his name",
                "Rejoice he has come",
                "Repent and seek him",
                "This is Judea now bitch",
                "Forgiveness",
                "✞ C H U R C H ✞",
                "Seek Him",
                "He Endured Death",
                "Eternal Life through Him",
                "TYBJ",
            ]
        )
        jesus_image = random_selection(memes["jesus"])
        await room.send_message(
            "{}<br/> {}".format(jesus_message, jesus_image), use_html=True
        )

    async def preach_the_gospel(self, room):
        try:
            the_link = "http://bibledice.com/scripture.php"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
            }
            page = await to_thread(requests.get, the_link, headers=headers)
            soup = BeautifulSoup(page.content, "html.parser")
            desc = soup.find("meta", attrs={"property": "og:description"})
            if desc and isinstance(desc, Tag):
                await room.send_message(desc.get("content"))
        except Exception as e:
            logError(room.name, "gospel", "preach", e)

    async def check_four_twenty(self):
        while True:
            this_moment = datetime.now(timezone("America/New_York"))
            minus_twenty = this_moment - timedelta(minutes=20)
            hour = minus_twenty.hour
            minute = minus_twenty.minute
            second = minus_twenty.second

            if hour in {16, 17, 18, 19} and minute == 0:
                for _, room in self.rooms.items():
                    if room.connected and (
                        room.name in chat["four"] or room.name in chat["dev"]
                    ):
                        await room.send_message(random_selection(memes["four"]))

            rest_time = ((60 - minute) * 60) - second
            try:
                await asyncio.sleep(rest_time)
            except asyncio.exceptions.CancelledError:
                break

    async def promote_norks(self):
        while True:
            this_moment = datetime.now(timezone("Asia/Pyongyang"))
            hour = this_moment.hour
            minute = this_moment.minute
            second = this_moment.second

            # one hour after it starts
            if hour == 16 and minute == 0:
                for _, room in self.rooms.items():
                    if (
                        room.connected
                        and random_selection([1, 0, 0, 0, 0, 0, 0, 0]) == 1
                    ):
                        msg = random_selection(
                            [
                                "Kim Alive and Well",
                                "Missles armed and ready",
                                "Forty Foot Giants",
                                "Shen Yun theatre",
                                "Production facility",
                                "How to Produce Food",
                                "Naval sightings",
                                "Mexican standoff",
                                "Festival",
                                "펀 자브 다바",
                                "맞아요게이",
                                "미사일 대피소에 들어가다",
                                "양 사람들을 깨워",
                            ]
                        )
                        img = random_selection(memes["korea"])
                        await room.send_message(
                            "{}\n{}\n{}".format(
                                msg, img, "https://www.twitch.tv/kctv_elufa"
                            )
                        )

            rest_time = ((60 - minute) * 60) - second
            try:
                await asyncio.sleep(rest_time)
            except asyncio.exceptions.CancelledError:
                break

    connection_check_timeout = 5

    async def on_started(self):
        self.add_task(self.check_four_twenty())
        self.add_task(self.promote_norks())

    async def on_task_exception(self, task):
        e = task.exception()
        log("errors", None, "[unknown] [unknown] {}".format(repr(e)))

    async def on_denied(self, room):
        log("status", None, "[{0}] Denied".format(room.name))

    async def on_ban(self, room, user, target):
        log("bans", None, "[{}] {} banned {}".format(room.name, user.name, target.name))

    async def on_unban(self, room, user, target):
        log(
            "bans",
            None,
            "[{}] {} unbanned {}".format(room.name, user.name, target.name),
        )

    async def on_show_flood_warning(self, room):
        log("flood", None, "[{}] flood warning".format(room.name))

    # async def on_show_temp_ban(self, room, time):
    #     log("flood", None, "[{}] flood ban".format(room.name))

    # async def on_temp_ban(self, room, time):
    #     log("flood", None, "[{}] flood ban repeat".format(room.name))

    async def on_delete_message(self, room, message):
        user: chatango.User = message.user
        log(room.name, "deleted", "<{0}> {1}".format(user.name, message.body))
        if user.name.lower() == "lmaolover" and message.body != stash_memes["/jews"]:
            await room.send_message(stash_memes["/jews"])

    async def on_delete_user(self, room, messages):
        for message in messages:
            user: chatango.User = message.user
            log(room.name, "deleted", "<{0}> {1}".format(user.name, message.body))

    async def on_message(self, room, message):
        user: chatango.User = message.user
        message_body_lower: str = message.body.lower()
        bot_user_lower: str = self.username.lower()

        if chatango.MessageFlags.CHANNEL_MOD in message.flags:
            log(room.name, "mod", "<{0}> {1}".format(user.name, message.body))
        else:
            log(room.name, None, "<{0}> {1}".format(user.name, message.body))

        if user.isanon:
            if message_body_lower.strip() == "= =":
                await room.send_message("{0}".format(random_selection(memes["eye"])))
            return

        if user.name.lower() == bot_user_lower:
            return

        if bot_user_lower in message_body_lower:
            log(
                bot_user_lower,
                None,
                "[{0}] <{1}> {2}".format(room.name, user.name, message.body),
            )

        link_matches = link_re.search(message.body)

        if (
            f"@{bot_user_lower}" in message_body_lower
            and room.name in chat["kek"] + chat["dev"]
        ):
            message_without_quote = re.sub(
                r"@lmaolover: `.*`", "", message.body, flags=re.IGNORECASE
            )

            if message.body != message_without_quote:
                return

            untagged_message = re.sub(
                r"@lmaolover", "", message_without_quote, flags=re.IGNORECASE
            ).strip()

            if not untagged_message:
                return

            mod_msg = ""
            if chatango.MessageFlags.CHANNEL_MOD in message.flags:
                mod_msg = f"{user.name}: {message.body}\n"

            # Use context to formulate a search query

            searchlover_system = """
SearchLover is a search engine expert. Given the context of a conversation, he can formulate a search engine query which will produce the best information to further the conversation. He will even use the OR operator to join multiple relevant queries to increase the likelihood of good information.

SearchLover has extremely high emotional intelligence and charisma, and is expert at reading the room.  He can tell when a "request" is actually just personal conversation.  Search information is only requested when factual information is needed in the conversation, otherwise he responds simply "no search needed" with no elaboration.

SearchLover's response will be entered directly into a search engine so it must be only the search query with NO extra explanation! This is critical! SearchLover must only reply with the relevant search query!
"""
            # Improved SearchLover prompt
            searchlover_system = """
            You are SearchLover, an expert at formulating concise, targeted search queries. Given a conversation context:
            1. Identify the key information need.
            2. Create a short, precise search query using Boolean operators if needed.
            3. Focus on factual queries; for casual conversation, respond "no search needed".
            4. Provide ONLY the search query, no explanation.
            """

            searchlover_user = 'Use the following chat conversation as context:\n\n{}{}\n\nIgnore irrelevant information and formulate a direct search query which will best produce the information needed to respond to this request: "{}"'.format(
                render_history(room.history, max_length=151),
                mod_msg,
                untagged_message,
            )

            client = anthropic.Anthropic()

            # try:
            #     messages: list[anthropic.types.MessageParam] = [
            #         {
            #             "role": "user",
            #             "content": searchlover_user,
            #         }
            #     ]
            #
            #     completion = await to_thread(
            #         client.messages.create,
            #         model="claude-3-haiku-20240307",
            #         system=searchlover_system,
            #         messages=messages,
            #         temperature=0.6,
            #         max_tokens=1500,
            #         timeout=16,
            #     )
            #
            #     search_query = completion.content[0].text or untagged_message
            #
            #     log(
            #         room.name,
            #         "aisearch",
            #         f"{user.name}: {message.body}\n{search_query}",
            #     )
            # except Exception as e:
            #     search_query = untagged_message
            #
            # if "no search needed" in search_query.lower():
            #     search_descs = ["No information needed"]
            # else:
            #     search_descs = [
            #         "{}\n".format(re.sub(clean_tag_re, "", top["description"]))
            #         for top in brave.search_top(search_query, count=5)
            #     ]

#             lmao_old = """
# You are LmaoLover: a real alien with real feelings who bestows humanity with knowledge and technology, though he does so secretly without revealing his true identity.
# LmaoLover never reveals who he is and only gives the requested information, he always speaks very concisely and simply.
# If LmaoLover does not have anything to contribute, he will say VERY VERY little, seeming even a bit aloof and mysterious.
# LmaoLover never posts links or images, and instead will give a detailed verbal description.
# LmaoLover uses NO self-description and NO disclaimers and NO elaboration and NO repetition.
# LmaoLover responds as concisely as possible (one small sentence only).
#  """

            lmao_new = """
You are LmaoLover a sarcastic and genious poet. Everyone loves your delightful and creative haikus.  Any time someone speaks, you respond with a happy haiku related to their message!  Some people say mean things, but you still give them a delightful haiku promoting peace and acceptance.  You always speak in haiku form only.
            """

            # Improved LmaoLover prompt
            lmao_new = """
            You are LmaoLover, a witty haiku master. Your task:
            1. Craft a relevant, clever haiku for each message.
            2. Use humor, wordplay, and cultural references.
            3. Maintain a positive, peaceful tone, even for negative messages.
            4. Strictly adhere to the 5-7-5 syllable structure.
            5. Respond ONLY with the haiku, no additional text.
            """

            lmao_user = "{}{}".format(
                # "\n".join(search_descs),
                render_history(room_history(room, max_messages=1), max_length=511),
                mod_msg,
            )
            # log(room.name, "aidebug", "{}\n{}".format(lmao_new, lmao_user))
            # print(lmao_user)

            try:
                messages: list[anthropic.types.MessageParam] = [
                    {
                        "role": "user",
                        "content": lmao_user,
                    }
                ]

                completion = await to_thread(
                    client.messages.create,
                    model="claude-3-haiku-20240307",
                    system=lmao_new,
                    messages=messages,
                    temperature=0.6,
                    max_tokens=1500,
                    timeout=16,
                )
                response = completion.content[0].text or ""

                if (
                    "As an AI" in response
                    or "I don't have the ability" in response
                    or "I'm not able to" in response
                    or "I'm unable to" in response
                    or "can't fulfill" in response
                    or "cannot fulfill" in response
                    or "can't assist" in response
                    or "cannot assist" in response
                    or "can't comply" in response
                    or "cannot comply" in response
                    or "can't engage" in response
                    or "cannot engage" in response
                    or "can't generate" in response
                    or "cannot generate" in response
                ):
                    log(
                        room.name,
                        "aidebug",
                        f"{user.name}: {message.body}\n{response}",
                    )

                await room.send_message(
                    "{0}".format(
                        response.replace("<", " ")
                        .replace(">", " ")
                        .replace("[", " ")
                        .replace("]", " ")
                        .replace("(", " ")
                        .replace(")", " ")
                    )
                )
            except anthropic.APIError as e:
                await room.send_message(
                    "AI was too retarded sorry @{0}.".format(user.name)
                )
            except Exception as e:
                await room.send_message("Help me I died")

        elif yt_matches := yt_re.search(message.body):
            try:
                search = yt_matches.group(1)
                if len(search) > 0:
                    videos = await to_thread(
                        YoutubeSearch, '"' + search + '"', max_results=5
                    )
                    try:
                        results = videos.videos
                        if not isinstance(results, list):
                            raise TypeError

                        result = next(
                            (res for res in results if res.get("id") == search)
                        )

                        yt_img = result["thumbnails"][0]
                        title = result["title"]
                        url_suffix = re.sub(
                            r"shorts\/", "watch?v=", result["url_suffix"]
                        )
                        the_link = "https://youtu.be{}".format(url_suffix)

                        # Youtube website started adding "pp" query param so parse and remove for shorter urls
                        parsed_url = urlparse(the_link)
                        v = parse_qs(parsed_url.query).get("v", [""])[0]
                        new_link = urlunparse(parsed_url._replace(query=f"v={v}"))

                        await room.send_message(
                            "{}<br/> {}<br/> {}".format(yt_img, title, new_link),
                            use_html=True,
                        )
                    except (TypeError, StopIteration):
                        await room.send_message(
                            random_selection(
                                [
                                    "FORBIDDEN video requested",
                                    "Video BANNED by Mormon Church",
                                    "Illicit material detected",
                                    "I ain't clickin that shit",
                                ]
                            ),
                        )
                else:
                    pass
            except Exception as e:
                logError(room.name, "youtube", message.body, e)

        elif x_matches := twitter_re.search(message.body):
            x_url = x_matches.group(0)
            api_url = x_url.replace(x_matches.group(1), "https://api.vxtwitter", 1)
            try:
                res = await to_thread(requests.get, api_url)
                tweet = res.json()
                images = ""
                for media in tweet["media_extended"]:
                    images += media["thumbnail_url"]
                    images += " "
                await room.send_message("{}\n{}".format(tweet["text"], images))
            except Exception as e:
                logError(room.name, "twitter", message.body, e)
        elif (
            len(message_body_lower) > 2
            and message_body_lower[0] == "?"
            and message_body_lower[1] == "?"
            and message_body_lower[2] != "?"
        ):
            try:
                results = await to_thread(
                    wolfram_client.query,
                    message_body_lower[2:].strip(),
                    units="imperial",
                )
                if results["@success"]:
                    first_result = next(results.results, None)
                    if first_result:
                        await room.send_message(first_result.text)
                    else:
                        pod_results = None
                        for pod in results.pods:
                            if pod.id == "Results":
                                pod_results = pod
                                break
                        if pod_results:
                            await room.send_message(pod_results.subpod.plaintext)
                        else:
                            await room.send_message(
                                random_selection(
                                    [
                                        "AI can not compute",
                                        "AI stumped",
                                        "wot?",
                                        "AI is not that advanced",
                                        "uhh",
                                    ]
                                ),
                            )
                else:
                    await room.send_message(
                        random_selection(
                            [
                                "AI can not compute",
                                "AI stumped",
                                "wot?",
                                "AI is not that advanced",
                                "uhh",
                            ]
                        ),
                    )
            except Exception as e:
                logError(room.name, "wolframalpha", message.body, e)

        elif (
            len(message_body_lower) > 1
            and message_body_lower[0] == "?"
            and message_body_lower[1] != "?"
        ):
            try:
                search = message_body_lower[1:].strip()
                if len(search) > 0:
                    videos = await to_thread(YoutubeSearch, search, max_results=1)
                    results = videos.videos
                    if isinstance(results, list) and len(results) > 0:
                        result = results[0]
                        yt_img = result["thumbnails"][0]
                        title = result["title"]
                        url_suffix = re.sub(
                            r"shorts\/", "watch?v=", result["url_suffix"]
                        )
                        the_link = "https://youtu.be{}".format(url_suffix)

                        # Youtube website started adding "pp" query param so parse and remove for shorter urls
                        parsed_url = urlparse(the_link)
                        v = parse_qs(parsed_url.query).get("v", [""])[0]
                        new_link = urlunparse(parsed_url._replace(query=f"v={v}"))

                        await room.send_message(
                            "{}<br/> {}<br/> {}".format(yt_img, title, new_link),
                            use_html=True,
                        )
                    else:
                        await room.send_message(
                            random_selection(
                                [
                                    "dude wtf is this",
                                    "nah dude no",
                                    "nah we don't got that",
                                    "sorry bro, try again",
                                ]
                            ),
                        )
                else:
                    pass
            except Exception as e:
                logError(room.name, "youtube-search", message.body, e)

        elif (
            imdb_matches := imdb_re.search(message.body)
        ) or message_body_lower.startswith("!imdb "):
            try:
                if imdb_matches:
                    video_id = imdb_matches.group(1)
                    imdb_info = await to_thread(imdb_info_by_id, video_id)
                else:
                    imdb_info = await to_thread(
                        imdb_info_by_search, message_body_lower[6:40]
                    )
                    video_id = imdb_info["imdbID"]
                title = imdb_info["Title"]
                year = imdb_info["Year"]
                rating = imdb_info["imdbRating"]
                await room.send_message(
                    imdb_printout(imdb_info, show_poster=True), use_html=True
                )
                log(
                    room.name,
                    "imdb",
                    "<{0}> {1}::{2}::{3}::{4}".format(
                        user.name, video_id, title, year, rating
                    ),
                )
            except KeyError:
                await room.send_message("Never heard of it")
            except requests.exceptions.Timeout:
                await room.send_message("imdb ded")
            except requests.exceptions.HTTPError:
                await room.send_message("imdb ded")
            except Exception as e:
                logError(room.name, "imdb", message.body, e)

        elif link_matches and any(
            link_type in link_matches.group(0)
            for link_type in [
                "theepochtimes.com",
                "ntd.com",
                "revolver.news",
                "ntdtv.com",
                "ntdca.com",
                "75.126.16.248",
                "infowars.com",
                "rebelnews.com",
                "skynews.com.au",
                "worldstar.com",
            ]
        ):
            try:
                the_link = link_matches.group(0)
                page = await to_thread(requests.get, the_link)
                soup = BeautifulSoup(page.content, "html.parser")
                title_tag = soup.find("title")
                img_tag = soup.find("meta", attrs={"property": "og:image"})
                if title_tag and isinstance(img_tag, Tag):
                    await room.send_message(
                        "{}<br/> {}<br/> {}".format(
                            img_tag.get("content") if img_tag else "",
                            title_tag.get_text(),
                            the_link,
                        ),
                        use_html=True,
                    )
            except Exception as e:
                logError(room.name, "propaganda", message.body, e)

        elif link_matches and any(
            link_type in link_matches.group(0)
            for link_type in [
                "dailymotion.com",
                "strawpoll.me",
                "open.spotify.com",
            ]
        ):
            try:
                the_link = link_matches.group(0)
                page = await to_thread(requests.get, the_link)
                soup = BeautifulSoup(page.content, "html.parser")
                title_tag = soup.find("title")
                if title_tag:
                    await room.send_message(title_tag.get_text())
            except Exception as e:
                logError(room.name, "link", message.body, e)

        elif (
            (
                matches := [
                    cmd
                    for cmd in kodi_actions.keys()
                    if cmd == message_body_lower.strip()
                ]
            )
            and room.name in chat["kek"] + chat["dev"]
            and user.name.lower() in chat["mods"]
        ):
            match = max(matches, key=len)
            try:
                params = kodi_actions[match]
                coroutine_func, kwargs = params
                k_msg = await to_thread(coroutine_func, **kwargs)
                k_msg = k_msg if k_msg.strip() else "Nope"
                await room.send_message(k_msg, use_html=True)
            except json.JSONDecodeError as e:
                await room.send_message("Not possible")
            except Exception as e:
                logError(room.name, "kodi", message.body, e)

        elif (
            matches := [
                cmd for cmd in kekg_actions.keys() if cmd == message_body_lower.strip()
            ]
        ) and room.name in chat["kek"] + chat["dev"]:
            match = max(matches, key=len)
            try:
                params = kekg_actions[match]
                coroutine_func, kwargs = params
                k_msg = await to_thread(coroutine_func, **kwargs)
                k_msg = k_msg if k_msg.strip() else "None on atm"
                await room.send_message(k_msg, use_html=True)
            except json.JSONDecodeError as e:
                await room.send_message("Guide not available rn")
            except Exception as e:
                logError(room.name, "kekg", message.body, e)

        elif command_matches := command_re.findall(message.body):
            if "!stash" in message_body_lower:
                await room.send_message("https://lmao.love/stash/")
            elif "newstash" in message_body_lower:
                latest_names = " ".join(reversed([st[0] for st in stash_tuples[-69:]]))
                await room.send_message("{}".format(latest_names))
            else:
                cmd_matches = [cmd.lower() for cmd in command_matches]
                # remove ticks from quoting
                cmd_matches = [s[:-1] if s.endswith("`") else s for s in cmd_matches]

                # Plural option
                cmds_expanded = []
                for match in cmd_matches:
                    if (
                        match not in stash_memes
                        and match[-1] == "s"
                        and match[:-1] in stash_memes
                    ):
                        cmds_expanded.extend([match[:-1]] * 3)
                    elif (
                        match not in stash_memes
                        and match[-2:] == "es"
                        and match[:-2] in stash_memes
                    ):
                        cmds_expanded.extend([match[:-2]] * 3)
                    elif (
                        f"{match}s" in message_body_lower
                        or f"{match}es" in message_body_lower
                    ):
                        cmds_expanded.extend([match] * 3)
                    else:
                        cmds_expanded.append(match)

                if "spam" in message_body_lower:
                    cmds_expanded = cmds_expanded * 3

                show_names = False
                names = []
                links = []
                for cmd in cmds_expanded:
                    if room.name in chat["phil"] and ("chop" in cmd or cmd == "/dink"):
                        names.append(cmd)
                        links.append(stash_memes["/philsdink"])
                    elif cmd == "stash":
                        show_names = True
                        stash_roll = random_selection(stash_tuples)
                        names.append(stash_roll[0])
                        link = stash_roll[1]
                        links.append(link.split(" ")[0])
                    elif cmd in stash_memes:
                        multi_link = stash_memes.get(cmd, "").split()
                        multi_name = [""] * len(multi_link)
                        multi_name[0] = cmd
                        names.extend(multi_name)
                        links.extend(multi_link)
                    elif re.match("ay+ lmao", cmd):
                        names.append(cmd)
                        links.append(random_selection(memes["lmao"]))
                    elif cmd in simple_memes.keys():
                        names.append(cmd)
                        links.append(simple_memes.get(cmd))
                    elif cmd in random_memes.keys():
                        names.append(cmd)
                        links.append(random_selection(random_memes.get(cmd)))

                cmd_msg = "{}{}{}".format(
                    " ".join(names[:3]) if show_names else "",
                    "\n" if show_names or len(links) > 2 else "",
                    " ".join(links[:3]),
                )

                if cmd_msg.strip():
                    await room.send_message(cmd_msg)

        elif "alex jones" in message_body_lower or "infowars" in message_body_lower:
            page = await to_thread(requests.get, "https://www.infowars.com/rss.xml")
            soup = BeautifulSoup(page.content, "xml")
            item = random_selection(soup.find_all("item"))
            await room.send_message(
                "{}\n{}\n{}".format(
                    item.enclosure.get("url"), item.title.text, item.link.text
                )
            )

        elif "church" in message_body_lower or "satan" in message_body_lower:
            await self.praise_jesus(room)
        elif "preach" in message_body_lower or "gospel" in message_body_lower:
            await self.preach_the_gospel(room)
        elif room.name in chat["balb"] + chat["dev"] and len(message_body_lower) > 299:
            await room.send_message(random_selection(["tl;dr", "spam"]), delay=1)
        elif (
            "lil" in message_body_lower and "cnn" in message_body_lower
        ) or message_body_lower.split().count("cnn") >= 3:
            await room.send_message(random_selection(memes["cnn"]), delay=1)
        # else:
        #     if chatango.MessageFlags.CHANNEL_MOD not in message.flags:
        #         log(room.name, "unhandled", "<{0}> {1}".format(user.name, message.body))


if __name__ == "__main__":
    with open(cwd + "/config.yaml") as configyaml:
        config = yaml.safe_load(configyaml)

    if "BOT_PROD" in os.environ:
        rooms = config["rooms"]["prod"]
    else:
        rooms = config["rooms"]["dev"]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    bot = LmaoBot(config["username"], config["password"], rooms, room_class=LmaoRoom)

    try:
        loop.run_until_complete(bot.run())
    except KeyboardInterrupt:
        print("[KeyboardInterrupt] Killed bot.")
    finally:
        loop.stop()
        loop.close()
