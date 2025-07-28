import os
import re
import json
import math
import time
import random
import requests
import threading
from guessit import guessit
from rapidfuzz import fuzz


cwd = os.path.dirname(os.path.abspath(__file__))
with open(cwd + "/kekg_memes.json", "r") as stashjson:
    kekg_config = json.load(stashjson)

number_mapping = kekg_config["number_mapping"]


KODI_URL = os.environ.get("KODI_URL")
KODI_AUTH = os.environ.get("KODI_AUTH")
FILES_ROOT = os.environ.get("FILES_ROOT")

# Module-level cache
_movies_cache = {"data": None, "timestamp": 0}
_cache_lock = threading.Lock()

# Cache expiration time (6 hour in seconds)
CACHE_EXPIRY = 18 * 3600


def progress():
    item = player_get_item()["item"]
    if item["type"] == "channel":
        channeldetails = channel_detail(item["id"])["channeldetails"]
        channelnumber = channeldetails["channelnumber"]
        broadcastnow = channeldetails["broadcastnow"]
        broadcastnext = channeldetails.get("broadcastnext")
        next_msg = ""
        if broadcastnext:
            percent_left = 100 - broadcastnow["progresspercentage"]
            seconds_left = broadcastnow["progress"] * (
                percent_left / broadcastnow["progresspercentage"]
            )
            next_msg = "\nNext: <b>{}</b> in {} minutes".format(
                broadcastnext["title"], math.floor(seconds_left / 60)
            )
        return "\n<b>{}</b> is {}% done\nStarted {} minutes ago on {}{}".format(
            broadcastnow["title"],
            math.floor(broadcastnow["progresspercentage"]),
            math.floor(broadcastnow["progress"] / 60),
            number_mapping.get(str(channelnumber)),
            next_msg,
        )
    elif item["type"] == "unknown":
        props = player_get_props()
        return "\n<b>{}</b> is {}% done\nCurrent: {}:{:0>2} - Total: {}:{:0>2}".format(
            item["label"],
            math.floor(props["percentage"]),
            props["time"]["hours"],
            props["time"]["minutes"],
            props["totaltime"]["hours"],
            props["totaltime"]["minutes"],
        )
    else:
        return "idk tbh"


def pixel_toggle():
    mode = player_get_view_mode()
    del mode["viewmode"]
    if mode["pixelratio"] == 1.0:
        props = player_get_props()
        if props.get("currentvideostream"):
            h = props["currentvideostream"]["height"]
            w = props["currentvideostream"]["width"]
            proper = 16 / 9
            real = w / h
            mode["pixelratio"] = math.sqrt(real / proper)
    else:
        mode["pixelratio"] = 1.0

    player_set_view_mode(mode)
    return "pixelratio: {:.2f}".format(mode["pixelratio"])


def player_get_view_mode():
    res = fetch_kodi("Player.GetViewMode")
    return res["result"]


def player_set_view_mode(viewmode):
    res = fetch_kodi("Player.SetViewMode", viewmode=viewmode)
    return res["result"]


def subs():
    item = player_get_item()["item"]
    if item["type"] == "channel":
        return "No subs on tv"
    elif item["type"] == "unknown":
        props = player_get_props()
        return "\nSUBS: {}\n".format("ON" if props["subtitleenabled"] else "OFF")
    else:
        return "idk tbh"


def directory_list(dirname):
    res = fetch_kodi("Files.GetDirectory", directory=dirname, sort={"method": "label"})
    return res["result"]


# Precompiled regexes
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
CLEAN_RE = re.compile(
    r"\b(720p|1080p|x264|x265|blu[- ]?ray|web[- ]?dl|remastered|ddp|h264|10bit|ac3|lama|evo)\b",
    re.IGNORECASE,
)


def extract_title_year_fast(name):
    name = name.replace(".", " ").replace("_", " ").lower()
    year_match = YEAR_RE.search(name)
    year = year_match.group(0) if year_match else ""
    cutoff_point = year_match.start() if year_match else name.find("1080p")
    if cutoff_point == -1:
        cutoff_point = len(name)
    title_part = name[:cutoff_point]
    title_cleaned = CLEAN_RE.sub("", title_part)
    title_cleaned = re.sub(r"\s+", " ", title_cleaned).strip()
    return title_cleaned, year


def group_and_deduplicate(filenames, threshold=92):
    filenames = list(filenames)  # make a mutable copy
    parsed = [(f, *extract_title_year_fast(f)) for f in filenames]
    used = set()
    deduped = []

    i = 0
    while i < len(parsed):
        if i in used:
            i += 1
            continue

        f1, title1, year1 = parsed[i]
        group = [i]
        used.add(i)

        for j in range(i + 1, len(parsed)):
            if j in used:
                continue
            f2, title2, year2 = parsed[j]

            if year1 and year2 and year1 != year2:
                continue  # Skip if year doesn't match

            similarity = fuzz.ratio(title1, title2)
            if similarity >= threshold:
                group.append(j)
                used.add(j)

        # if len(group) > 1:
        #     print("Group:")
        #     for idx in group:
        #         print("  ", filenames[idx])
        #     print()

        # Keep only the first item of the group
        deduped.append(filenames[group[0]])

        i += 1

    return deduped


def movies_root():
    global _movies_cache

    current_time = time.time()

    # Check if we need to refresh the cache
    with _cache_lock:
        cache_age = current_time - _movies_cache["timestamp"]
        cache_valid = _movies_cache["data"] is not None and cache_age < CACHE_EXPIRY

        if cache_valid:
            return _movies_cache["data"]
        else:
            data = directory_list(FILES_ROOT)["files"]

            data_labels = [item["label"] for item in data]
            deduped_labels = group_and_deduplicate(data_labels)

            # Update cache
            _movies_cache["data"] = deduped_labels
            _movies_cache["timestamp"] = current_time

            return _movies_cache["data"]


def random_selection(list):
    return list[random.randint(0, len(list) - 1)]


def random_movie():
    all_movies = movies_root()
    movie_str = "\n"
    for _ in range(5):
        selected_movie = random_selection(all_movies)
        guessed_movie = guessit(selected_movie)
        guessed_title = guessed_movie.get("title", "Untitled")
        guessed_year = guessed_movie.get("year", "")
        movie_str = movie_str + f"{guessed_title} {guessed_year}\n"
    return movie_str


def current_movie_dir():
    # get current item
    # determine folder path if file movie
    pass


def full_settings_print():
    props = setting_sections()
    for sec in props["sections"]:
        print("*** {} ({}) - {} ***".format(sec["label"], sec["id"], sec["help"]))
        cats = setting_categories(sec["id"])
        for cat in cats["categories"]:
            print("{} ({}) - {}".format(cat["label"], cat["id"], cat.get("help")))
            setts = get_settings(sec["id"], cat["id"])
            for sett in setts["settings"]:
                print(
                    "- {} ({}) - {}".format(
                        sett.get("label"), sett.get("id"), sett.get("help")
                    )
                )
            print()
        print("\n")


def setting_sections():
    res = fetch_kodi("Settings.GetSections")
    return res["result"]


def setting_categories(section=""):
    res = fetch_kodi("Settings.GetCategories", section=section)
    return res["result"]


def get_settings(section="", category=""):
    res = fetch_kodi(
        "Settings.GetSettings", filter={"section": section, "category": category}
    )
    return res["result"]


def player_get_item():
    res = fetch_kodi("Player.GetItem", playerid=1)
    return res["result"]


def player_get_props():
    props = [
        "type",
        # "partymode",
        # "speed",
        "time",
        "percentage",
        "totaltime",
        "playlistid",
        # "position",
        # "repeat",
        # "shuffled",
        # "canseek",
        # "canchangespeed",
        # "canmove",
        # "canzoom",
        # "canrotate",
        # "canshuffle",
        # "canrepeat",
        # "currentaudiostream",
        # "audiostreams",
        "subtitleenabled",
        "currentsubtitle",
        "subtitles",
        # "live",
        "currentvideostream",
        "videostreams",
        "cachepercentage",
    ]
    res = fetch_kodi("Player.GetProperties", playerid=1, properties=props)
    return res["result"]


def pvr():
    props = [
        # "thumbnail",
        # "channeltype",
        # "hidden",
        # "locked",
        "channel",
        # "lastplayed",
        # "broadcastnow",
        # "broadcastnext",
        # "uniqueid",
        # "icon",
        "channelnumber",
        # "subchannelnumber",
        # "isrecording",
        # "hasarchive",
        # "clientid"
    ]

    # Channel group 3 = HD Channels
    res = fetch_kodi("PVR.GetChannels", channelgroupid=3, properties=props)
    print(res)
    for chan in res["result"]["channels"]:
        print(
            "{}\t{}\t{}\t{}".format(
                chan["channelid"], chan["channelnumber"], chan["label"], chan["channel"]
            )
        )


def channel_detail(id):
    props = [
        "thumbnail",
        "channeltype",
        "channel",
        "lastplayed",
        "broadcastnow",
        "broadcastnext",
        "icon",
        "channelnumber",
        # "uniqueid",
        # "clientid"
    ]
    res = fetch_kodi("PVR.GetChannelDetails", channelid=id, properties=props)
    return res["result"]


def fetch_kodi(method, **kwargs):
    if KODI_URL and KODI_AUTH:
        headers = {
            "content-type": "application/json",
            "Authorization": "Basic {}".format(KODI_AUTH),
        }

        data = {"jsonrpc": "2.0", "method": method, "params": kwargs, "id": 1}

        response = requests.post(KODI_URL, json=data, headers=headers)
        return json.loads(response.content)
    else:
        raise ValueError("KODI_URL and/or KODI_AUTH is not set")
