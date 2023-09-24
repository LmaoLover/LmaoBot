import os
import json
import math
from lassie import Lassie


def lassie():
    lass = Lassie()
    lass.request_opts = {"timeout": 10}
    return lass


cwd = os.path.dirname(os.path.abspath(__file__))
with open(cwd + "/kekg_memes.json", "r") as stashjson:
    kekg_config = json.load(stashjson)

sports_labels = kekg_config["sports_labels"]
movies_labels = kekg_config["movies_labels"]
label_mapping = kekg_config["label_mapping"]


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
    return [ch["label"] for ch in channels if "label" in ch]


def sports():
    channels = filter_channels(labels=sports_labels)
    lines = []
    for ch in channels:
        now = ch.get("broadcastnow")
        if now:
            channel = label_mapping.get(ch.get("label"), ch.get("label"))
            on_now = now.get("title")
            if (
                on_now.startswith("*")
                and "College" not in on_now
                and "High School" not in on_now
            ):
                lines.append(f"<b>{on_now[1:]}</b> - {channel}")
    return "\n".join(lines)


def egg():
    channels = filter_channels(programs=["*College Football"])
    lines = []
    for ch in channels:
        now = ch.get("broadcastnow")
        if now:
            channel = label_mapping.get(ch.get("label"), ch.get("label"))
            on_now = now.get("title", " ")
            desc = now.get("plot")
            if desc.startswith("All the action"):
                continue
            desc = desc.replace("No. ", "#")
            desc = desc.replace("St.", "Saint")
            desc = desc[: desc.find(".")] if "." in desc else desc
            lines.append(f"<b>{on_now[1:]}</b> - {channel}\n{desc}")
    return "\n".join(lines)


def is_show(broadcast):
    return broadcast.get("runtime", 0) <= 60


def is_not_show(broadcast):
    return broadcast.get("runtime", 0) > 60 and not broadcast.get(
        "title", ""
    ).startswith("*")


def always_true(_):
    return True


def shows(spam=False):
    return starting_now(filter_channels(), is_show, spam)


def movies(spam=False):
    return starting_now(filter_channels(labels=movies_labels), is_not_show, spam)


def starting_now(channels, test=always_true, spam=False):
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
                started.append(
                    "<b>{}</b> - {} - {}% done{}".format(
                        now.get("title"),
                        label_mapping.get(channel.get("label"), channel.get("label")),
                        math.floor(now_prog),
                        f"\n{now.get('plot','')[:275]}\n" if spam else "",
                    )
                )
            elif next and now_remaining <= 15 and test(next):
                coming_up.append(
                    "<b>{}</b> - {} - In {} minutes{}".format(
                        next.get("title"),
                        label_mapping.get(channel.get("label"), channel.get("label")),
                        now_remaining,
                        f"\n{next.get('plot','')[:275]}\n" if spam else "",
                    )
                )

    return "\n{}\n{}".format(
        "\n".join(started),
        "\n".join(coming_up),
    )
