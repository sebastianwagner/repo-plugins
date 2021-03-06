import requests
from BeautifulSoup import BeautifulSoup as BS

BASE_URL="https://www.newyankee.com/watch/"


def get_first_select_options(dom):
    options_list = dom.findAll('select')[0].findAll('option')[1:]
    options_objs = [[x.text,dict(x.attrs)] for x in options_list]
    active_options = [x for x in options_objs if "disabled" not in x[1]]
    keypairs = [[x[0],x[1]['value']] for x in active_options] 
    return keypairs

def get_second_select_options(dom):
    options_list = dom.findAll('select')[1].findAll('option')[1:]
    options_objs = [[x.text,dict(x.attrs)] for x in options_list]
    keypairs = [[x[0],x[1]['value']] for x in options_objs]
    return keypairs

def extract_mp4(resp_text):
    mp4_url_start = resp_text.find('https://content.jwplatform.com')
    resp_sub1 = resp_text[mp4_url_start:]
    mp4_url_end = resp_sub1.find('.mp4') + 4
    mp4_url = resp_sub1[:mp4_url_end]
    return mp4_url

def get_season_list():
    resp_text = requests.get(BASE_URL).text
    dom = BS(resp_text)
    return get_first_select_options(dom)

def get_episode_list(season):
    resp_text = requests.post(BASE_URL, data={'nyw_season':season}).text
    dom = BS(resp_text)
    return get_second_select_options(dom)

def get_episode(season, episode):
    resp_text = requests.post(BASE_URL, data={'nyw_season':season, 'nyw_episode':episode}).text
    return extract_mp4(resp_text)



