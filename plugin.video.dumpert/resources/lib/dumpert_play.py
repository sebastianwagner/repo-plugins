#
# Imports
#
from BeautifulSoup import BeautifulSoup
from dumpert_const import __addon__, __settings__, __language__, __images_path__, __date__, __version__
from dumpert_utils import HTTPCommunicator
import os
import re
import base64
import ast
import sys
import urllib, urllib2
import urlparse
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

#
# Main class
#
class Main:
	#
	# Init
	#
	def __init__( self ) :
		# Get plugin settings
		self.DEBUG = __settings__.getSetting('debug')
		self.VIDEO = __settings__.getSetting('video')
		
		if (self.DEBUG) == 'true':
			xbmc.log( "[ADDON] %s v%s (%s) debug mode, %s = %s, %s = %s" % ( __addon__, __version__, __date__, "ARGV", repr(sys.argv), "File", str(__file__) ), xbmc.LOGNOTICE )
		
		# Parse parameters...
		self.video_page_url = urlparse.parse_qs(urlparse.urlparse(sys.argv[2]).query)['video_page_url'][0]
		
		if (self.DEBUG) == 'true':
			xbmc.log( "[ADDON] %s v%s (%s) debug mode, %s = %s" % ( __addon__, __version__, __date__, "self.video_page_url", str(self.video_page_url) ), xbmc.LOGNOTICE )

		#
		# Play video...
		#
		self.playVideo()
	
	#
	# Play video...
	#
	def playVideo( self ) :
		#
		# Init
		#
		no_url_found = False
		unplayable_media_file = False
		have_valid_url = False
		
		#
		# Get current list item details...
		#
		title     	  = unicode( xbmc.getInfoLabel( "ListItem.Title"  ), "utf-8" )
		thumbnail_url =          xbmc.getInfoImage( "ListItem.Thumb"  )
		studio    	  = unicode( xbmc.getInfoLabel( "ListItem.Studio" ), "utf-8" )
		plot          = unicode( xbmc.getInfoLabel( "ListItem.Plot"   ), "utf-8" )
		genre         = unicode( xbmc.getInfoLabel( "ListItem.Genre"  ), "utf-8" )
		
		#
		# Show wait dialog while parsing data...
		#
		dialogWait = xbmcgui.DialogProgress()
		dialogWait.create( __language__(30504), title )
		
		httpCommunicator = HTTPCommunicator()
		
		try:
			html_data = httpCommunicator.get ( self.video_page_url )
		except urllib2.HTTPError, error:
			if (self.DEBUG) == 'true':
				xbmc.log( "[ADDON] %s v%s (%s) debug mode, %s = %s" % ( __addon__, __version__, __date__, "HTTPError", str(error) ), xbmc.LOGNOTICE )
			dialogWait.close()
			del dialogWait
			xbmcgui.Dialog().ok( __language__(30000), __language__(30507) % (str(error) ))
			exit(1)

		soup = BeautifulSoup(html_data)

		#<div class="videoplayer" id="video1" data-files="eyJmbHYiOiJodHRwOlwvXC9tZWRpYS5kdW1wZXJ0Lm5sXC9mbHZcLzI4OTE2NWRhXzEwMjU1NzUyXzYzODMxODA4OTU1NDc2MV84MTk0MzU3MDVfbi5tcDQuZmx2IiwidGFibGV0IjoiaHR0cDpcL1wvbWVkaWEuZHVtcGVydC5ubFwvdGFibGV0XC8yODkxNjVkYV8xMDI1NTc1Ml82MzgzMTgwODk1NTQ3NjFfODE5NDM1NzA1X24ubXA0Lm1wNCIsIm1vYmlsZSI6Imh0dHA6XC9cL21lZGlhLmR1bXBlcnQubmxcL21vYmlsZVwvMjg5MTY1ZGFfMTAyNTU3NTJfNjM4MzE4MDg5NTU0NzYxXzgxOTQzNTcwNV9uLm1wNC5tcDQiLCJzdGlsbCI6Imh0dHA6XC9cL3N0YXRpYy5kdW1wZXJ0Lm5sXC9zdGlsbHNcLzY1OTM1MjRfMjg5MTY1ZGEuanBnIn0="></div></div>	
		video_urls = soup.findAll('div', attrs={'class': re.compile("video")}, limit=1)
		if len(video_urls) == 0:
			no_url_found = True
		else:
			video_url_enc = video_urls[0]['data-files']
			#base64 decode
			video_url_dec = str(base64.b64decode(video_url_enc))
			#{"flv":"http:\/\/media.dumpert.nl\/flv\/5770e490_Jumbo_KOOP_DAN__Remix.avi.flv","tablet":"http:\/\/media.dumpert.nl\/tablet\/5770e490_Jumbo_KOOP_DAN__Remix.avi.mp4","mobile":"http:\/\/media.dumpert.nl\/mobile\/5770e490_Jumbo_KOOP_DAN__Remix.avi.mp4","720p":"http:\/\/media.dumpert.nl\/720p\/5770e490_Jumbo_KOOP_DAN__Remix.avi.mp4","still":"http:\/\/static.dumpert.nl\/stills\/6593503_5770e490.jpg"}
			
			if (self.DEBUG) == 'true':
				xbmc.log( "[ADDON] %s v%s (%s) debug mode, %s = %s" % ( __addon__, __version__, __date__, "video_url_dec", str(video_url_dec) ), xbmc.LOGNOTICE )

			#convert string to dictionary
			video_url_dec_dict = ast.literal_eval(video_url_dec)
			
			#matching the desired and available quality
			if self.VIDEO == '0':
				try:
					video_url = str(video_url_dec_dict['mobile'])
				except KeyError:
					no_url_found = True
			elif self.VIDEO == '1':
 				try:
				 	video_url =  str(video_url_dec_dict['tablet'])
 				except KeyError:
 					try: 
 					 	video_url = str(video_url_dec_dict['mobile'])
 					except KeyError:
 						no_url_found = True
 			elif self.VIDEO == '2':
 				try:
				 	video_url = str(video_url_dec_dict['720p'])
 			 	except KeyError:
 			 		try:
 			 		 	video_url =  str(video_url_dec_dict['tablet'])
 			 		except KeyError:	
 			 			try:
 			 			 	video_url =  str(video_url_dec_dict['mobile'])			 	
 			 			except KeyError:
 			 			 	no_url_found = True
 			 			 	
 			video_url = video_url.replace('\/','/')
			if (self.DEBUG) == 'true':
				xbmc.log( "[ADDON] %s v%s (%s) debug mode, %s = %s" % ( __addon__, __version__, __date__, "video_url", str(video_url) ), xbmc.LOGNOTICE )

			if httpCommunicator.exists( video_url ):
				have_valid_url = True
			else:
				unplayable_media_file = True
		
		# Play video...
		if have_valid_url:
			playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
			playlist.clear()
		
			listitem = xbmcgui.ListItem( title, iconImage="DefaultVideo.png", thumbnailImage=thumbnail_url )
			xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=True, listitem=listitem)
			listitem.setInfo( "video", { "Title": title, "Studio" : "Dumpert", "Plot" : plot, "Genre" : genre } )
			playlist.add( video_url, listitem )
	
			# Close wait dialog...
			dialogWait.close()
			del dialogWait
			
			# Play video...
			xbmcPlayer = xbmc.Player()
			xbmcPlayer.play( playlist )
		#
		# Alert user
		#
	 	elif no_url_found:
			xbmcgui.Dialog().ok( __language__(30000), __language__(30505))
		elif unplayable_media_file:
			xbmcgui.Dialog().ok( __language__(30000), __language__(30506))
	
#
# The End
#