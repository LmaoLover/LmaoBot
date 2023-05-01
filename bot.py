import os
import ch
import re
import json
import yaml
import random
import requests
import twitter
from lassie import Lassie
from pytz import timezone
from calendar import timegm
from datetime import datetime, timedelta
from time import gmtime
from youtube_search import YoutubeSearch
from urllib.parse import urlparse, urlunparse, parse_qs
from wolframalpha import Client
from collections import deque
from dotenv import load_dotenv

load_dotenv()
import openai

cwd = os.path.dirname(os.path.abspath(__file__))

def lassie():
    lass = Lassie()
    lass.request_opts = {'timeout': 3}
    return lass


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
    if filename[-10:] == '_memes.txt':
        meme_type = filename[:-10]
        memes[meme_type] = [line.rstrip('\n') for line in open(cwd + '/' + filename)]

with open(cwd + '/countries.yaml','r') as countriesyaml:
    countries = yaml.safe_load(countriesyaml)

with open(cwd + '/rooms.yaml','r') as roomsyaml:
    chat = yaml.safe_load(roomsyaml)

with open(cwd + '/twitter.yaml','r') as twitteryaml:
    keys = yaml.safe_load(twitteryaml)
    tw_api = twitter.Api(**keys, tweet_mode='extended')

with open(cwd + '/wolfram.yaml','r') as wolframyaml:
    keys = yaml.safe_load(wolframyaml)
    wolfram_client = Client(keys['app_id'])

with open(cwd + '/stash_memes.json','r') as stashjson:
    stash_memes = json.load(stashjson)

stash_tuples = [(k, v) for k, v in stash_memes.items()]

link_re = re.compile(r"https?://\S+")
command_re = re.compile(r"\/[^\s]*")
yt_re = re.compile(
    r"(?:youtube(?:-nocookie)?\.com/(?:[^/]+/.+/|(?:v|e(?:mbed)?)/|.*[?&]v=)|youtu\.be/|shorts/)([a-zA-Z0-9_-]{11})")
imdb_re = re.compile(
    r"(?:.*\.|.*)imdb.com/(?:t|T)itle(?:\?|/)(..\d+)")
twitter_re = re.compile(
    r"twitter.com/[a-zA-Z0-9_]+/status/([0-9]+)", re.IGNORECASE)
insta_re = re.compile(
    r"instagram.com/p/[a-zA-Z0-9_-]+", re.IGNORECASE)

class LmaoBot(ch.RoomManager):
    def __init__(self, name=None, password=None, pm=True):
        ch.RoomManager.__init__(self, name, password, pm)
        self.room_states = {}

    def onInit(self):
        self.setNameColor("000000")
        self.setFontColor("000000")
        self.setFontFace("sans-serif")
        self.setFontSize(11)

    def room_message(self, room, msg, **kwargs):
        msg = msg[:1798]

        delay_time = kwargs.pop('delay', None)
        if delay_time:
            self.setTimeout(delay_time, self.room_message, room, msg, **kwargs)
            return

        queue = self.room_states[room.name]['queue']

        if not queue:
            self.setTimeout(0, self.pop_queue, room)
        queue.append([msg, kwargs])

    def pop_queue(self, room):
        queue = self.room_states[room.name]['queue']

        if queue:
            slow_mode = room.name in chat['balb']
            previous_msg_time = self.room_states[room.name]['last_msg_time']
            current_msg_time = timegm(gmtime())
            time_since_last_msg = current_msg_time - previous_msg_time

            if slow_mode and time_since_last_msg < 5:
                try_again_in = 6 - time_since_last_msg
                self.setTimeout(try_again_in, self.pop_queue, room)
                return

            # Sending it
            msg, kwargs = queue.popleft()
            self.room_states[room.name]['last_msg_time'] = current_msg_time
            room.message(msg, **kwargs)

            if queue:
                try_again_in = 5 if slow_mode else 0
                self.setTimeout(try_again_in, self.pop_queue, room)

    def praise_jesus(self, room):
        jesus_message = random_selection(["Thank You Based Jesus","Praise him","Lost sheep return to me","Praise in his name",
                                          "Rejoice he has come","Repent and seek him","This is Judea now bitch","Forgiveness",
                                          "✞ C H U R C H ✞","Seek Him","He Endured Death","Eternal Life through Him","TYBJ"])
        jesus_image   = random_selection(memes['jesus'])
        self.room_message(room, "{}<br/> {}".format(jesus_message, jesus_image), html=True)

    def preach_the_gospel(self, room):
        try:
            the_link = "http://bibledice.com/scripture.php"
            fetch = lassie().fetch(the_link)
            self.room_message(room, fetch['description'])
        except Exception as e:
            logError(room.name, "gospel", "preach", e)

    def check_four_twenty(self, room):
        if room.connected:
            this_moment = datetime.now(timezone("America/New_York"))
            minus_twenty = this_moment - timedelta(minutes=20)
            hour = minus_twenty.hour
            minute = minus_twenty.minute
            second = minus_twenty.second

            if hour in {16, 17, 18, 19} and minute == 0 and room.name in chat['kek']:
                self.room_message(room, random_selection(memes['four']))

            # double duty ronaldo tax
            # if hour in {22, 23, 0, 1} and minute == 0 and random_selection([1, 0, 0, 0, 0, 0, 0]) == 1:
            #     self.room_message(room, random_selection(memes['ronaldo']))

            rest_time = ((60 - minute) * 60) - second
            self.setTimeout(rest_time, self.check_four_twenty, room)

    def promote_norks(self, room):
        if room.connected:
            this_moment = datetime.now(timezone("Asia/Pyongyang"))
            hour = this_moment.hour
            minute = this_moment.minute
            second = this_moment.second

            # one hour after it starts
            if hour == 16 and minute == 0 and random_selection([1, 0, 0, 0, 0, 0, 0, 0]) == 1:
                msg = random_selection(["Kim Alive and Well", "Missles armed and ready", "Footy Highlights", "Shen Yun theatre",
                                        "Production facility", "How to Produce Food", "Naval sightings", "Mexican standoff",
                                        "Festival", "펀 자브 다바", "맞아요게이", "미사일 대피소에 들어가다","양 사람들을 깨워"])
                img = random_selection(memes['korea'])
                self.room_message(room, "{} <br/> {} <br/> https://lmao.love/korea/".format(msg, img), html=True)

            rest_time = ((60 - minute) * 60) - second
            self.setTimeout(rest_time, self.promote_norks, room)

    def onConnect(self, room):
        log("status", None, "[{0}] Connected".format(room.name))
        self.room_states[room.name] = { 'last_msg_time': 0, 'queue': deque() }
        if room.name in chat['balb'] + chat['kek']:
            self.check_four_twenty(room)
            # self.promote_norks(room)

    def onDisconnect(self, room):
        log("status", None, "[{0}] Disconnected".format(room.name))
        self.room_states.pop(room.name, None)
        self.leaveRoom(room.name)
        self.setTimeout(110, self.stop)

    def onReconnect(self, room):
        log("status", None, "[{0}] Reconnected".format(room.name))

    def onBan(self, room, user, target):
        log("bans", None, "[{}] {} banned {}".format(room.name, user.name, target.name))

    def onUnban(self, room, user, target):
        log("bans", None, "[{}] {} unbanned {}".format(room.name, user.name, target.name))

    def onFloodWarning(self, room):
        log("flood", None, "[{}] flood warning".format(room.name))

    def onFloodBan(self, room):
        log("flood", None, "[{}] flood ban".format(room.name))

    def onFloodBanRepeat(self, room):
        log("flood", None, "[{}] flood ban repeat".format(room.name))

    def onRaw(self, room, raw):
        #if raw and room.name == "debugroom":
        #    log(room.name, "raw", raw)
        pass

    def onMessageDelete(self, room, user, message):
        log(room.name, "deleted", "<{0}> {1}".format(user.name, message.body))
        if user.name.lower() == "lmaolover" and message.body != "https://lmao.love/stash/memes/jews.gif":
            self.room_message(room, "https://lmao.love/stash/memes/jews.gif")

    def onMessage(self, room, user, message):
        log(room.name, None, "<{0}> {1}".format(user.name, message.body))

        if "lmaolover" == user.name.lower():
            return

        if user.name[0] == '!' or user.name[0] == '#':
            room.deleteMessage(message)
            return

        message_body_lower = message.body.lower()

        if "lmaolover" in message_body_lower:
            log("lmaolover", None, "[{0}] <{1}> {2}".format(room.name, user.name, message.body))

        lil_cnn     = "lil" in message_body_lower and "cnn" in message_body_lower
        cnn_cnn_cnn = message_body_lower.split().count('cnn') >= 3

        link_matches = link_re.search(message.body)
        command_matches = command_re.search(message.body)
        yt_matches   = yt_re.search(message.body)
        imdb_matches = imdb_re.search(message.body)
        twitter_matches = twitter_re.search(message.body)
        insta_matches = insta_re.search(message.body)
        other_links = ["worldstar", "dailymotion.com", "liveleak.com", "strawpoll.me", "open.spotify.com"]
        other_image = ["worldstar"]
        other_link_matches = link_matches and any(link_type in link_matches.group(0) for link_type in other_links)
        other_image_matches = other_link_matches and any(link_type in link_matches.group(0) for link_type in other_image)
        propaganda_links = ["theepochtimes.com", "ntd.com", "revolver.news", "ntdtv.com", "ntdca.com", "75.126.16.248",
                            "infowars.com", "rebelnews.com", "skynews.com.au"]
        propaganda_link_matches = link_matches and any(link_type in link_matches.group(0) for link_type in propaganda_links)

        country_match = next((country for country in countries if country in message_body_lower), None)

        if "@lmaolover" in message_body_lower and room.name in chat['kek'] + chat['dev']:
            message_without_quote = re.sub(r"@lmaolover: `.*`", "", message_body_lower)
            untagged_message = re.sub(r"@lmaolover", "", message_without_quote)

            if untagged_message.strip() and message_body_lower == message_without_quote:
                racism_mode = False
                try:
                    messages=[
                        {"role": "system", "content": "You are a gray alien, haiku artist, pimp and drug dealer."},
                        {"role": "system", "content": "You will do a haiku randomly ten percent of the time."},
                        {"role": "user", "content": untagged_message[:160]}
                    ]
                    completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages, temperature=0.6, max_tokens=340, request_timeout=7)
                    response = completion.choices[0].message.content

                    if response.startswith("I'm sorry") or response.startswith("Sorry") or "language model" in response:
                        racism_mode = True
                    else:
                        self.room_message(room, "{0}".format(response))
                except openai.error.Timeout as e:
                    racism_mode = True
                except Exception as e:
                    self.room_message(room, "{0}".format(e))

                if racism_mode:
                    try:
                        prompt="""
                        LmaoLover is a gray alien, rapper, pimp and drug dealer.
                        He always adds jokes to his responses, and is often toxic.
                        He does not know details about sports and will do a haiku instead.

                        {1}: {0}
                        LmaoLover:""".format(untagged_message[:160], user.name)
                        completion = openai.Completion.create(engine="text-davinci-003", prompt=prompt, temperature=0.6, max_tokens=340, request_timeout=10)
                        self.room_message(room, "{0}".format(completion.choices[0].text))
                    except openai.error.Timeout as e:
                        self.room_message(room, "AI was too slow sorry mate.")
                    except Exception as e:
                        self.room_message(room, "{0}".format(e))

        elif "lmao?" in message_body_lower:
            roger_messages = ["sup", "hey girl", "ayyyy", "Let's get this bread", "What you need?", "Yo waddup"]
            self.room_message(room, random_selection(roger_messages))

        elif room.name in chat['balb'] + chat['dev'] and len(message_body_lower) > 299:
            self.room_message(room, random_selection(["tl;dr","spam"]), delay=1)

        elif yt_matches:
            try:
                search = yt_matches.group(1)
                if len(search) > 0:
                    results = YoutubeSearch('"' + search + '"', max_results=5).videos
                    if len(results) > 0 and next((res for res in results if res["id"] == search), None):
                        result = next((res for res in results if res['id'] == search), None)
                        yt_img = result['thumbnails'][0]
                        title = result['title']
                        url_suffix = re.sub(r'shorts\/', 'watch?v=', result['url_suffix'])
                        the_link = "https://youtu.be{}".format(url_suffix)

                        # Youtube website started adding "pp" query param so parse and remove for shorter urls
                        parsed_url = urlparse(the_link)
                        v = parse_qs(parsed_url.query).get('v', [''])[0]
                        new_link = urlunparse(parsed_url._replace(query=f'v={v}'))

                        self.room_message(room, "{}<br/> {}<br/> {}".format(yt_img, title, new_link), html=True)
                    else:
                        self.room_message(room, random_selection(['FORBIDDEN video requested','Video BANNED by Mormon Church','Illicit material detected',"I ain't clickin that shit"]))
                else:
                    pass
            except Exception as e:
                logError(room.name, "youtube", message.body, e)

        elif len(message_body_lower) > 2 and message_body_lower[0] == '?' and message_body_lower[1] == '?' and message_body_lower[2] != '?':
            try:
                results = wolfram_client.query(message_body_lower[2:].strip())
                if results['@success']:
                    first_result = next(results.results, None)
                    if first_result:
                        self.room_message(room, first_result.text)
                    else:
                        pod_results = None
                        for pod in results.pods:
                            if pod.id == 'Results':
                                pod_results = pod
                                break
                        if pod_results:
                            self.room_message(room, pod_results.subpod.plaintext)
                        else:
                            self.room_message(room, random_selection(["AI can not compute","AI stumped","wot?","AI is not that advanced","uhh"]))
                else:
                    self.room_message(room, random_selection(["AI can not compute","AI stumped","wot?","AI is not that advanced","uhh"]))
            except Exception as e:
                logError(room.name, "wolframalpha", message.body, e)

        elif len(message_body_lower) > 1 and message_body_lower[0] == '?' and message_body_lower[1] != '?':
            try:
                search = message_body_lower[1:].strip()
                if len(search) > 0:
                    results = YoutubeSearch(search, max_results=1).videos
                    if len(results) > 0:
                        result = results[0]
                        yt_img = result['thumbnails'][0]
                        title = result['title']
                        url_suffix = re.sub(r'shorts\/', 'watch?v=', result['url_suffix'])
                        the_link = "https://youtu.be{}".format(url_suffix)

                        # Youtube website started adding "pp" query param so parse and remove for shorter urls
                        parsed_url = urlparse(the_link)
                        v = parse_qs(parsed_url.query).get('v', [''])[0]
                        new_link = urlunparse(parsed_url._replace(query=f'v={v}'))

                        self.room_message(room, "{}<br/> {}<br/> {}".format(yt_img, title, new_link), html=True)
                    else:
                        self.room_message(room, random_selection(['dude wtf is this','nah dude no',"nah we don't got that",'sorry bro, try again']))
                else:
                    pass
            except Exception as e:
                logError(room.name, "youtube-search", message.body, e)

        elif imdb_matches:
            try:
                video_id = imdb_matches.group(1)
                imdb_api = 'http://www.omdbapi.com/?apikey=cc41196e&i=' + video_id
                imdb_resp = requests.get(imdb_api, timeout=3)
                imdb_resp.raise_for_status()

                imdb_info = imdb_resp.json()
                poster = imdb_info['Poster']
                title = imdb_info['Title']
                year = imdb_info['Year']
                rating = imdb_info['imdbRating']
                plot = imdb_info['Plot']
                self.room_message(room, "{0}<br/> {1} ({2}) [{3}/10]<br/> <i>{4}</i>".format(
                    poster, title, year, rating, plot), html=True)
                log(room.name, "imdb", "<{0}> {1}::{2}::{3}::{4}".format(user.name, video_id, title, year, rating))
            except requests.exceptions.Timeout:
                self.room_message(room, "imdb ded")
            except requests.exceptions.HTTPError:
                self.room_message(room, "imdb ded")
            except Exception as e:
                logError(room.name, "imdb", message.body, e)

        elif twitter_matches and user.name != 'broiestbro':
            try:
                status_id = twitter_matches.group(1)
                tweet = tw_api.GetStatus(status_id, trim_user=True)
                desc = tweet.full_text
                img = ''
                if tweet.media:
                    img = next(media.media_url_https for media in tweet.media)
                if "satan" in desc.lower():
                    self.praise_jesus(room)
                else:
                    self.room_message(room, "{}<br/> {}".format(desc, img), html=True)
            except Exception as e:
                # just try again for connection error
                try:
                    status_id = twitter_matches.group(1)
                    tweet = tw_api.GetStatus(status_id, trim_user=True)
                    desc = tweet.full_text
                    img = ''
                    if tweet.media:
                        img = next(media.media_url for media in tweet.media)
                    if "satan" in desc.lower():
                        self.praise_jesus(room)
                    else:
                        self.room_message(room, "{}<br/> {}".format(desc, img), html=True)
                except Exception as e:
                    logError(room.name, "twitter", message.body, e)

        elif insta_matches:
            self.room_message(room, random_selection(memes['insta']))

        elif propaganda_link_matches and room.name in chat['mod']:
            try:
                the_link = link_matches.group(0)
                fetch = lassie().fetch(the_link, favicon=False)
                desc = fetch['title']
                img = ''
                if fetch['images']:
                    urls = (img['src'] for img in fetch['images'])
                    img = next(urls, '')
                room.deleteMessage(message)
                self.room_message(room, "{}<br/> {}<br/> {}".format(img, desc, the_link), html=True)
            except Exception as e:
                logError(room.name, "propaganda", message.body, e)

        elif other_image_matches:
            try:
                fetch = lassie().fetch(link_matches.group(0))
                desc = fetch['title']
                img = ''
                if fetch['images']:
                    urls = (img['src'] for img in fetch['images'] if
                            'type' in img and img['type'] == 'og:image')
                    img = next(urls, '')
                self.room_message(room, "{}<br/> {}".format(desc, img), html=True)
            except Exception as e:
                logError(room.name, "link_image", message.body, e)

        elif other_link_matches:
            try:
                the_link = link_matches.group(0)
                fetch = lassie().fetch(the_link)
                self.room_message(room, fetch['title'])
            except Exception as e:
                logError(room.name, "link", message.body, e)

        elif re.match("ay+ lmao", message_body_lower):
            self.room_message(room, random_selection(memes['lmao']))
        elif re.match(".*(?<![@a-zA-Z])clam.*", message_body_lower):
            self.room_message(room, random_selection(memes['clam']))

        elif command_matches:
            try:
                command = command_matches.group(0).lower()
                if room.name in chat['phil'] and "chop" in command:
                    self.room_message(room, "https://i.imgur.com/fnAVXWe.gif")
                else:
                    self.room_message(room, stash_memes[command])
            except:
                pass

        # elif "alex jones" in message_body_lower or "infowars" in message_body_lower:
        #     self.room_message(room, "https://lmao.love/infowars")
        elif "church" in message_body_lower or "satan" in message_body_lower:
            self.praise_jesus(room)
        elif "preach" in message_body_lower or "gospel" in message_body_lower:
            self.preach_the_gospel(room)
        elif "maga" in message_body_lower and "magazine" not in message_body_lower:
            self.room_message(room, random_selection(memes['trump']))
        elif "!whatson" in message_body_lower:
            self.room_message(room, "https://guide.lmao.love/")
        elif "!stash" in message_body_lower:
            meme = random_selection(stash_tuples)
            self.room_message(room, "{}<br/> {}".format(meme[0], meme[1]), html=True)
        elif "stash" in message_body_lower:
            meme = random_selection(stash_tuples)
            self.room_message(room, "{}<br/> {}".format(meme[0], meme[1]), html=True)
            # self.room_message(room, random_selection(memes['stash']))
        elif "!jameis" in message_body_lower or "!winston" in message_body_lower:
            self.room_message(room, "https://i.imgur.com/vyrNpSm.png")
        elif "!phins" in message_body_lower:
            self.room_message(room, "https://giphygifs.s3.amazonaws.com/media/Px2Zu55ofxfO0/giphy.gif")
        elif "!spike" in message_body_lower:
            self.room_message(room, "https://xvsvc.net/emotes/1smoke.gif")
        elif "tyson" in message_body_lower:
            self.room_message(room, random_selection(memes['tyson']))
        elif "pika" in message_body_lower:
            self.room_message(room, "https://i.imgur.com/dZxHsel.png")
        elif "propaganda" in message_body_lower:
            self.room_message(room, random_selection(memes['korea']))
        elif "xmas" in message_body_lower or "christmas" in message_body_lower:
            self.room_message(room, random_selection(memes['santa']))
        elif "shkreli" in message_body_lower:
            self.room_message(room, random_selection(memes['shkreli']))
        elif "jumanji" in message_body_lower:
            self.room_message(room, random_selection(memes['jumanji']))
        elif "devil?" in message_body_lower:
            self.room_message(room, "https://i.imgur.com/kz3joDl.jpg")
        elif "go2bed" in message_body_lower:
            self.room_message(room, "https://i.imgur.com/hpZ64Zk.jpg")
        elif "gil2bed" in message_body_lower:
            self.room_message(room, "https://i.imgur.com/8SwlIv8.png")
        elif "ronaldo" in message_body_lower or "rolando" in message_body_lower or "penaldo" in message_body_lower:
            self.room_message(room, random_selection(memes['ronaldo']))
        # elif "!tv" in message_body_lower:
        #     if country_match:
        #         country_code = countries[country_match]
        #         country_name = country_match.title()
        #         self.room_message(room, "{} TV<br/> https://lmao.love/{}/".format(country_name, country_code), html=True, delay=1)
        #     else:
        #         self.room_message(room, "https://lmao.love")
        elif lil_cnn or cnn_cnn_cnn:
            self.room_message(room, random_selection(memes['cnn']), delay=1)


if __name__ == "__main__":
    with open(cwd + '/config.yaml') as configyaml:
        config = yaml.safe_load(configyaml)

    if 'BOT_PROD' in os.environ:
        rooms = config['rooms']['prod']
    else:
        rooms = config['rooms']['dev']

    while True:
        bot = LmaoBot(config['username'], config['password'])
        try:
            for room in rooms:
                bot.joinRoom(room)
            bot.main()
        except KeyboardInterrupt:
            print("")
            bot.stop()
            break
