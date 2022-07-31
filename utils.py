import json
import pywikibot
import requests


def file_get_contents(filename):
    with open(filename, 'r', encoding='UTF-8') as f:
        s = f.read()
    return s


def file_put_contents(filename, content):
    with open(filename, 'w', encoding='UTF-8') as f:
        f.write(content)


def load_json_file(filename):
    return json.loads(file_get_contents(filename))


def fetch_url(url):
    return requests.get(url, headers={'User-Agent': 'elise/0.1'}, allow_redirects=False)


def fetch_url_json(url):
    return json.loads(requests.get(url, headers={'User-Agent': 'elise/0.1'}, allow_redirects=False).text)


def get_site():
    site = pywikibot.Site('wikidata', 'wikidata')
    site.login()
    return site
