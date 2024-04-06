import os
import json
import math
import requests

cwd = os.path.dirname(os.path.abspath(__file__))
with open(cwd + "/kekg_memes.json", "r") as stashjson:
    kekg_config = json.load(stashjson)

number_mapping = kekg_config["number_mapping"]


KODI_URL = os.environ.get("KODI_URL")
KODI_AUTH = os.environ.get("KODI_AUTH")
FILES_ROOT = os.environ.get("FILES_ROOT")


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


def movies_root():
    return directory_list(FILES_ROOT)


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
