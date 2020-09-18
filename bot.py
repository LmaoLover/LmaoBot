import sys
import os
import ch
import re
import pdb
import json
import yaml
import random
import requests
import twitter
from lassie import Lassie
from pytz import timezone
from calendar import timegm
from datetime import datetime, time, timedelta
from time import gmtime, strftime, sleep
from urllib.request import urlopen
from urllib.parse import parse_qs
from lxml import html

cwd = os.path.dirname(os.path.abspath(__file__))

def lassie():
    l = Lassie()
    l.request_opts = { 'timeout': 3 }
    return l

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

with open(cwd + '/stash_memes.json','r') as stashjson:
    stash_memes = json.load(stashjson)

stash_tuples = [(k, v) for k, v in stash_memes.items()]

link_re = re.compile(r"https?://\S+")
command_re = re.compile(r"\/[^\s]*")
yt_re = re.compile(
    r"(?:youtube(?:-nocookie)?\.com/(?:[^/]+/.+/|(?:v|e(?:mbed)?)/|.*[?&]v=)|youtu\.be/)([a-zA-Z0-9_-]{11})")
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
        delay_time = kwargs.pop('delay', None)
        if delay_time:
            self.setTimeout(delay_time, self.room_message, room, msg, **kwargs)
            return

        previous_msg_time = self.room_states[room.name]['last_msg_time']
        current_msg_time = timegm(gmtime())
        time_since_last_msg = current_msg_time - previous_msg_time

        if time_since_last_msg <= 5:
            just_drop_it = kwargs.pop('drop', None)
            if just_drop_it != True:
                try_again_in = 6 - time_since_last_msg
                self.setTimeout(try_again_in, self.room_message, room, msg, **kwargs)
            return

        self.room_states[room.name]['last_msg_time'] = current_msg_time
        room.message(msg, **kwargs)

    def praise_jesus(self, room):
        jesus_message = random_selection(["JESUS IS LORD","TYBJ","PRAISE HIM"])
        jesus_image   = random_selection(memes['jesus'])
        self.room_message(room, "{}<br/> {}".format(jesus_message, jesus_image), html=True)

    def preach_the_gospel(self, room):
        try:
            the_link = "http://bibledice.com/scripture.php"
            fetch = lassie().fetch(the_link)
            self.room_message(room, fetch['description'])
        except Exception as e:
            logError(room.name, "gospel", message.body, e)

    def check_four_twenty(self, room):
        if room.connected:
            this_moment = datetime.now(timezone("America/New_York"))
            minus_twenty = this_moment - timedelta(minutes=20)
            hour = minus_twenty.hour
            minute = minus_twenty.minute
            second = minus_twenty.second

            if hour in {16, 17, 18, 19} and minute == 0:
                self.room_message(room, random_selection(memes['four']))

            #hacked for political purposes
            if hour in {22, 23, 0, 1} and minute == 0 and room.name in chat['balb'] :
                self.room_message(room, random_selection(memes['biden']))

            rest_time = ((60 - minute) * 60) - second
            self.setTimeout(rest_time, self.check_four_twenty, room)

    def promote_norks(self, room):
        if room.connected:
            this_moment = datetime.now(timezone("Asia/Pyongyang"))
            hour = this_moment.hour
            minute = this_moment.minute
            second = this_moment.second

            if hour == 15 and minute == 0:
                msg = random_selection(["Dear Leader requests your presence!",
                                        "Rejoice for 3pm has arrived again!",
                                        "Korean Truth Broadcast Begins Now!"])
                self.room_message(room, "{} <br/> https://lmao.love/korea/ (!tv)".format(msg), html=True)

            rest_time = ((60 - minute) * 60) - second
            self.setTimeout(rest_time, self.promote_norks, room)

    def onConnect(self, room):
        log("status", None, "[{0}] Connected".format(room.name))
        self.room_states[room.name] = { 'last_msg_time': 0 }
        if room.name in chat['balb'] + chat['kek'] + chat['dev']:
            self.check_four_twenty(room)
            #self.promote_norks(room)

    def onDisconnect(self, room):
        log("status", None, "[{0}] Disconnected".format(room.name))
        self.room_states.pop(room.name, None)
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
        if user.name.lower() == "lmaolover" and message.body != "https://media1.giphy.com/media/gSI0RTsif0w1i/giphy.gif":
            self.room_message(room, "https://media1.giphy.com/media/gSI0RTsif0w1i/giphy.gif")

    def onMessage(self, room, user, message):
        log(room.name, None, "<{0}> {1}".format(user.name, message.body))

        if "lmaolover" == user.name.lower():
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
        other_links = ["facebook.com", "worldstar", "dailymotion.com",
                "liveleak.com", "strawpoll.me", "open.spotify.com", "banned.video"]
        other_image = ["worldstar", "banned.video"]
        other_link_matches = link_matches and any(link_type in link_matches.group(0) for link_type in other_links)
        other_image_matches = other_link_matches and any(link_type in link_matches.group(0) for link_type in other_image)

        country_match = next((country for country in countries if country in message_body_lower ), None)

        if "@lmaolover" in message_body_lower:
            user_lower = user.name.lower()
            message_without_quote = re.sub(r"@lmaolover: `.*`", "", message_body_lower)

            apologies = ["sry", "sorry", "apolog", "forgive"]
            repentant = any(apol in message_without_quote for apol in apologies)
            if repentant:
                self.room_message(room, "thank you friend", delay=2)

            rude_messages = ["kys", "get fukt", "shit bot", "fuck you", "fuck off", "fuck ur", "fuck up", "stfu"]
            disrespected = any(rude in message_without_quote for rude in rude_messages)
            rude_response = ["fix the @{} problem when", "back in yer cage @{}"]
            if disrespected:
                self.room_message(room, random_selection(rude_response).format(user.name), delay=2)

        elif room.name in chat['balb'] + chat['dev'] and len(message_body_lower) > 299:
            self.room_message(room, random_selection(["tl;dr","spam"]), delay=1)

        elif yt_matches:
            video_id = yt_matches.group(1)
            yt_api = 'https://youtube.com/get_video_info?video_id=' + video_id
            with urlopen(yt_api) as response:
                try:
                    response_text = response.read().decode('utf-8')
                    response_qs = parse_qs(response_text)
                    response_js = json.loads(response_qs['player_response'][0])
                    video_details = response_js['videoDetails']
                    title = video_details['title']
                    rating = video_details['averageRating']
                    vid_seconds = int(video_details['lengthSeconds'])
                    yt_img = video_details['thumbnail']['thumbnails'][0]['url']
                    is_live = video_details['isLiveContent']
                    if vid_seconds < 3600:
                        length = strftime("%M:%S", gmtime(vid_seconds))
                    else:
                        length = strftime("%H:%M:%S", gmtime(vid_seconds))
                    if is_live:
                        self.room_message(room, "{0} [{1:.2f}/5]<br/> {2}".format(title, rating, yt_img), html=True)
                    else:
                        self.room_message(room, "{0} ({1}) [{2:.2f}/5]<br/> {3}".format(title, length, rating, yt_img), html=True)
                    log(room.name, "youtube", "<{0}> {1}::{2}::{3:.2f}".format(user.name, video_id, title, rating))
                except Exception as e:
                    logError(room.name, "youtube", message.body, e)

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

        elif twitter_matches:
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

        # twitter is cringe
        # elif twitter_matches:
        #     try:
        #         tw_html = requests.get('https://'+twitter_matches.group(0)).text
        #         dom = html.fromstring(tw_html)
        #         desc = next(iter(dom.xpath('//meta[@property="og:description"]/@content')))
        #         og_images = dom.xpath('//meta[@property="og:image"]/@content')
        #         img = next((img for img in og_images if 'profile_images' not in img), '')
        #         if "satan" in desc.lower():
        #             self.praise_jesus(room)
        #         else:
        #             self.room_message(room, "{}<br/> {}".format(desc[1:-1], img), html=True)
        #     except Exception as e:
        #         logError(room.name, "twitter", message.body, e)

        elif insta_matches:
            self.room_message(room, random_selection(memes['insta']))

        # instagram is cringe
        # elif insta_matches:
        #     try:
        #         fetch = lassie().fetch('https://'+insta_matches.group(0))
        #         desc = fetch['title']
        #         img = ''
        #         if fetch['images']:
        #             urls = (img['src'] for img in fetch['images'] if
        #                     'type' in img and img['type'] == 'og:image')
        #             img = next(urls, '')
        #         self.room_message(room, "{}<br/> {}".format(desc, img), html=True)
        #     except Exception as e:
        #         logError(room.name, "insta", message.body, e)
            
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
                command = command_matches.group(0)
                self.room_message(room, stash_memes[command])
            except:
                pass

        elif "alex jones" in message_body_lower or "infowars" in message_body_lower:
            self.room_message(room, "https://lmao.love/infowars")
        elif "truth" in message_body_lower:
            self.room_message(room, "https://lmao.love/truth")
        elif "church" in message_body_lower or "satan" in message_body_lower:
            self.praise_jesus(room)
        elif "preach" in message_body_lower or "gospel" in message_body_lower:
            self.preach_the_gospel(room)
        elif "maga" in message_body_lower and "magazine" not in message_body_lower:
            self.room_message(room, random_selection(memes['trump']))
        elif "!stash" in message_body_lower:
            meme = random_selection(stash_tuples)
            self.room_message(room, "{}<br/> {}".format(meme[0], meme[1]), html=True, drop=True)
        # elif "stash" in message_body_lower:
        #     self.room_message(room, random_selection(memes['stash']))
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
        elif "!tv" in message_body_lower:
            if country_match:
                country_code = countries[country_match]
                country_name = country_match.title()
                self.room_message(room, "{} TV<br/> https://lmao.love/{}/".format(country_name, country_code), html=True, delay=1)
            else:
                self.room_message(room, "https://lmao.love")
        elif room.name in chat['balb'] + chat['dev'] and (lil_cnn or cnn_cnn_cnn):
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
            break;
