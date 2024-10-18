import os
from mcstatus import JavaServer

KRAFT_URL = os.environ.get("KRAFT_URL")


def who_krafting():
    if KRAFT_URL:
        server_status = JavaServer.lookup(KRAFT_URL).status()
        players = server_status.players.sample
        if players and len(players) > 0:
            return "Krafters: ({})\n{}".format(
                len(players), "\n".join([p.name for p in players])
            )
        else:
            return "Lads: NONE"
    else:
        raise ValueError("KRAFT_URL is not set")
