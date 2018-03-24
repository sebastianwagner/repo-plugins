# -*- coding: utf-8 -*-
import json
import libmediathek3 as libMediathek
base = 'https://www.funk.net/api/v3.0'

fanart = libMediathek.fanart

types = {
'format':'formats',
'series':'series',
}

#v3.0
#auth = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnROYW1lIjoiY3VyYXRpb24tdG9vbCIsInNjb3BlIjoic3RhdGljLWNvbnRlbnQtYXBpLGN1cmF0aW9uLWFwaSxzZWFyY2gtYXBpIn0.q4Y2xZG8PFHai24-4Pjx2gym9RmJejtmK6lMXP5wAgc'
#v3.1
auth = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnROYW1lIjoiY3VyYXRpb24tdG9vbC12Mi4wIiwic2NvcGUiOiJzdGF0aWMtY29udGVudC1hcGksY3VyYXRpb24tc2VydmljZSxzZWFyY2gtYXBpIn0.SGCC1IXHLtZYoo8PvRKlU2gXH1su8YSu47sB3S4iXBI'

#auth = 'eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJjbGllbnROYW1lIjoiY3VyYXRpb24tdG9vbCIsInNjb3BlIjoic3RhdGljLWNvbnRlbnQtYXBpLGN1cmF0aW9uLWFwaSxzZWFyY2gtYXBpIn0.'
#eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnROYW1lIjoiY3VyYXRpb24tdG9vbCIsInNjb3BlIjoic3RhdGljLWNvbnRlbnQtYXBpLGN1cmF0aW9uLWFwaSxzZWFyY2gtYXBpIn0.q4Y2xZG8PFHai24-4Pjx2gym9RmJejtmK6lMXP5wAgc
#eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnROYW1lIjoiY3VyYXRpb24tdG9vbC12Mi4wIiwic2NvcGUiOiJzdGF0aWMtY29udGVudC1hcGksY3VyYXRpb24tc2VydmljZSxzZWFyY2gtYXBpIn0.SGCC1IXHLtZYoo8PvRKlU2gXH1su8YSu47sB3S4iXBI
header = 	{
			'Authorization':auth,
			'Accept-Encoding':'gzip',
			}

def parseMain():
	onlySeries = libMediathek.getSetting('skipToSeries') == 'true'
	response = libMediathek.getUrl(base+'/content/channels/?size=100',header)
	j = json.loads(response)
	l = []
	for item in j['result']:
		if item['type'] == 'Series' or not onlySeries:
			try:
				d = {}
				d['_name'] = item['title']
				if 'shortDescription' in item:
					d['_plot'] = item['shortDescription']
				if 'description' in item:
					d['_plot'] = item['description']
				d['_thumb'] = item['imageUrlSquare']
				if 'imageUrlOrigin' in item:
					d['_fanart'] = item['imageUrlOrigin']
				d['_type'] = 'dir'
				d['id'] = item['alias']
				if item['type'] == 'Series':
					d['mode'] = 'listSeasons'
				elif item['type'] == 'Format':
					d['mode'] = 'listVideos'
				
					
				l.append(d)
			except:
				libMediathek.log(json.dumps(item))
	return l
	
	
def parseSeasons(id):
	response = libMediathek.getUrl(base+'/content/playlists/filter/?channelId=' + id + '&secondarySort=alias,ASC',header)
	j = json.loads(response)
	l = []
	for item in j['result']:
		d = {}
		d['_name'] = item['title']
		if 'shortDescription' in item:
			d['_plot'] = item['shortDescription']
		if 'description' in item:
			d['_plot'] = item['description']
		d['_thumb'] = item['imageUrlPortrait']
		d['_fanart'] = item['imageUrlOrigin']
		d['_mpaa'] = str(item['fsk'])
		#d['_type'] = 'dir'
		d['_type'] = 'season'
		d['id'] = item['alias']
		d['mode'] = 'listEpisodes'
		l.append(d)
	return l
	
def parseEpisodes(id):
	response = libMediathek.getUrl(base+'/content/playlists/'+id+'/videos/?size=100&secondarySort=episodeNr,ASC',header)
	j = json.loads(response)
	l = []
	for item in j['result']:
		d = {}
		d['_name'] = item['title']
		if 'shortDescription' in item:
			d['_plot'] = item['shortDescription']
		if 'description' in item:
			d['_plot'] = item['description']
		d['_thumb'] = item['imageUrlOrigin']
		d['_duration'] = item['duration']
		d['_season'] = item['seasonNr']
		d['_episode'] = item['episodeNr']
		d['_mpaa'] = 'FSK ' + str(item['fsk'])
		d['_type'] = 'video'
		d['sourceId'] = item['sourceId']
		d['mode'] = 'play'
		l.append(d)
	return l
	
def parseVideos(id):
	#https://www.funk.net/api/v3.0/content/videos/filter?channelId=auf-einen-kaffee-mit-moritz-neumeier&page=0&size=20
	response = libMediathek.getUrl(base+'/content/videos/filter?channelId='+id+'&page=0&size=100',header)
	j = json.loads(response)
	l = []
	for item in j['result']:
		d = {}
		d['_name'] = item['title']
		if 'shortDescription' in item:
			d['_plot'] = item['shortDescription']
		if 'description' in item:
			d['_plot'] = item['description']
		d['_thumb'] = item['imageUrlOrigin']
		d['_duration'] = item['duration']
		d['_mpaa'] = 'FSK ' + str(item['fsk'])
		d['_type'] = 'video'
		d['sourceId'] = item['sourceId']
		d['mode'] = 'play'
		l.append(d)
	return l
