import os
import json
import math
from lassie import Lassie
from datetime import datetime, timedelta
import pytz
from imdb import imdb_info_by_search, imdb_printout


def lassie():
    lass = Lassie()
    lass.request_opts = {"timeout": 10}
    return lass


cwd = os.path.dirname(os.path.abspath(__file__))
with open(cwd + "/kekg_memes.json", "r") as stashjson:
    kekg_config = json.load(stashjson)

sports_labels = kekg_config["sports_labels"]
movies_labels = kekg_config["movies_labels"]
shows_labels = kekg_config["shows_labels"]
number_mapping = kekg_config["number_mapping"]


KEKG_URL = os.environ.get("KEKG_URL")


def fetch_kekg():
    fetch = lassie().fetch(KEKG_URL)
    return json.loads(fetch["html"])


def filter_channels(labels=[], programs=[]):
    kekg_json = fetch_kekg()
    channels = kekg_json["result"]["channels"]

    filtered = []
    for ch in channels:
        label_match = not labels or ch["label"] in labels
        program_match = not programs or (
            ch["broadcastnow"] and ch["broadcastnow"]["title"] in programs
        )
        if label_match and program_match:
            filtered.append(ch)

    return filtered


def channel_names():
    channels = filter_channels()
    lines = [
        '"{}": "{}",'.format(
            ch.get("channelnumber"),
            ch.get("channel"),
        )
        for ch in channels
    ]
    return "\n".join(lines)


def good_sports(broadcast) -> bool:
    on_now = broadcast.get("title")
    return (
        on_now.startswith("*")
        and "College" not in on_now
        and "High School" not in on_now
    )


def sports(spam=False):
    started, coming_up = starting_now(
        filter_channels(labels=sports_labels), good_sports, default_now=True
    )
    shows = started + coming_up
    return "\n{}".format(
        "\n".join(program_printout(ch, br, spam) for ch, br in shows),
    )


def egg():
    channels = filter_channels(programs=["*College Football"])
    lines = []
    for ch in channels:
        now = ch.get("broadcastnow")
        if now:
            channel = number_mapping.get(str(ch.get("channelnumber")), ch.get("label"))
            on_now = now.get("title", " ")
            desc = now.get("plot")
            if desc.startswith("All the action"):
                continue
            desc = desc.replace("No. ", "#")
            desc = desc.replace("St.", "Saint")
            desc = desc[: desc.find(".")] if "." in desc else desc
            lines.append(f"<b>{on_now[1:]}</b> - {channel}\n{desc}")
    return "\n" + "\n".join(lines)


def is_show(broadcast) -> bool:
    return broadcast.get("runtime", 0) <= 60


def is_not_show(broadcast) -> bool:
    return broadcast.get("runtime", 0) > 60 and not broadcast.get(
        "title", ""
    ).startswith("*")


def runs_over_jeop(broadcast) -> bool:
    start = broadcast.get("starttime")
    end = broadcast.get("endtime")
    if not start or not end:
        return False

    eastern_timezone = pytz.timezone("US/Eastern")
    startdate = (
        datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
        .replace(tzinfo=pytz.UTC)
        .astimezone(eastern_timezone)
    )
    enddate = (
        datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
        .replace(tzinfo=pytz.UTC)
        .astimezone(eastern_timezone)
    )

    jeop_start = startdate.replace(hour=19, minute=5, second=0, microsecond=0)

    if startdate.time() > jeop_start.time():
        jeop_start += timedelta(days=1)

    if jeop_start.weekday() > 4:
        return False

    return startdate.time() < jeop_start.time() and enddate.time() > jeop_start.time()


def good_movie(broadcast) -> bool:
    return is_not_show(broadcast) and not runs_over_jeop(broadcast)


def is_genre(broadcast, genre) -> bool:
    try:
        return broadcast.get("genre", False) and genre in broadcast.get("genre")
    except TypeError:
        return False


def bad_movie(broadcast) -> bool:
    return is_genre(broadcast, "Movie") and not runs_over_jeop(broadcast)


def sports_genre(broadcast) -> bool:
    return is_genre(broadcast, "Sports")


def always_true(_) -> bool:
    return True


def shows(spam=False):
    started, coming_up = starting_now(
        filter_channels(labels=shows_labels), is_show, default_now=True
    )
    shows = started + coming_up
    return "\n{}".format(
        "\n".join(program_printout(ch, br, spam) for ch, br in shows),
    )


def movies(spam=False, imdb=False):
    started, coming_up = starting_now(filter_channels(labels=movies_labels), good_movie)
    movies = started + coming_up
    if imdb:
        printer = imdb_extra_printout
    else:
        printer = program_printout
    return "\n{}".format(
        "\n".join(printer(ch, br, spam) for ch, br in starttime_sorted(movies)),
    )


def movies_alt():
    started, coming_up = starting_now(filter_channels(), bad_movie)
    movies = started + coming_up
    return "\n{}".format(
        "\n".join(program_printout(ch, br, plot=False) for ch, br in movies),
    )


def sports_alt():
    started, coming_up = starting_now(filter_channels(), sports_genre, default_now=True)
    shows = started + coming_up
    return "\n{}".format(
        "\n".join(program_printout(ch, br, plot=False) for ch, br in shows),
    )


def starttime_sorted(channel_broadcasts):
    return sorted(channel_broadcasts, key=lambda b: b[1].get("starttime", ""))


def program_printout(channel, broadcast, plot=False):
    return "<b>{}</b> - {} - {}{}".format(
        broadcast.get("title"),
        number_mapping.get(str(channel.get("channelnumber")), channel.get("label")),
        program_timing(broadcast),
        f"\n{broadcast.get('plot','')[:275]}\n" if plot else "",
    )


def imdb_extra_printout(channel, broadcast, plot=True):
    try:
        imdb_info = imdb_info_by_search(broadcast.get("title"))
        channel_time = " - {} - {}".format(
            number_mapping.get(str(channel.get("channelnumber")), channel.get("label")),
            program_timing(broadcast),
        )
        return imdb_printout(imdb_info, show_poster=False, extra_info=channel_time)
    except KeyError:
        return ""


def program_timing(broadcast):
    try:
        current_time = datetime.now(pytz.UTC)
        starttime = datetime.strptime(
            broadcast.get("starttime", ""), "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=pytz.UTC)

        if starttime > current_time:
            time_until = starttime - current_time
            now_remaining = str(round(time_until.total_seconds() / 60))
            return "In {} minutes".format(now_remaining)
        else:
            now_prog = broadcast.get("progresspercentage", 50)
            return "{}% done".format(math.floor(now_prog))

    except ValueError:
        return ""


# Returns two lists of (channel, broadcast)
def starting_now(channels, test=always_true, default_now=False):
    started = []
    coming_up = []
    for channel in channels:
        now = channel.get("broadcastnow")
        next = channel.get("broadcastnext")

        if now:
            now_prog = now.get("progresspercentage", 50)
            now_starting = now_prog < 15
            now_remaining = math.floor(
                ((now.get("runtime", 420) * 60) - now.get("progress", 210 * 60)) / 60
            )
            if now_starting and test(now):
                started.append((channel, now))
            elif next and now_remaining <= 15 and test(next):
                coming_up.append((channel, next))
            elif default_now and test(now):
                started.append((channel, now))

    return started, coming_up
