import requests
from urllib.parse import quote


def imdb_info_by_search(query: str):
    imdb_api = "http://www.omdbapi.com/?apikey=cc41196e&t=" + quote(query)
    imdb_resp = requests.get(imdb_api, timeout=5)
    imdb_resp.raise_for_status()

    return imdb_resp.json()


def imdb_info_by_id(video_id: str):
    imdb_api = "http://www.omdbapi.com/?apikey=cc41196e&i=" + video_id
    imdb_resp = requests.get(imdb_api, timeout=5)
    imdb_resp.raise_for_status()

    return imdb_resp.json()


def imdb_printout(imdb_info: dict, show_poster=True):
    poster = imdb_info["Poster"]
    title = imdb_info["Title"]
    year = imdb_info["Year"]
    rating = imdb_info["imdbRating"]
    plot = imdb_info["Plot"]
    return "{}<br/><b>{}</b> ({}) [{}/10]<br/><i>{}</i>".format(
        f"{poster}<br/>" if show_poster else "", title, year, rating, plot
    )
