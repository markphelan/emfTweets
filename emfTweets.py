#!/usr/bin/env python

import pygame as pg
import os
import sys
import time
import io
from PIL import Image, ImageDraw, ImageFont
from urllib2 import urlopen
import datetime
from tweepy import Stream
from tweepy import OAuthHandler
from tweepy.streaming import StreamListener
import json
import random
import re
import signal 
import pprint
import cups
import textwrap
import collections
import pytz
import netifaces as ni

# Get local IP address for eth0
ni.ifaddresses('eth0')
ip = ni.ifaddresses('eth0')[2][0]['addr']

# Convert timestamps in tweets to "local time"
def tweetTime(tweetTimestamp):
 tz_local = pytz.timezone('Europe/London')
 utc=pytz.utc
 localTime =(utc.localize(datetime.datetime.strptime(tweetTimestamp,'%a %b %d %H:%M:%S +0000 %Y')).astimezone(tz_local)).strftime("%Y-%m-%d %H:%M:%S")
 return localTime

filter = "emfcamp"
printing = 1 # enable/disable sending print jobs
cutPaper = 0 # doesn't work - just configure in the driver
debug = 0

# twitter keys
ckey=""
csecret=""
atoken=""
asecret=""

# screen resolution (this is the resolution designed to run at, changing it will break stuff in this version)
scrWidth=1050
scrHeight=1680

# colours
white = (255,255,255)
black = (0,0,0)
red = (128,0,0)
green = (0,128,0)
emfPurple = (22,17,35)

lastxpos = lastypos = 0
lastWidth = lastHeight = 0

# List to keep track of tweets
tweetList = collections.deque(maxlen=6)

# tweet object to hold necessary data
class tweet:
 def __init__(self,tweet,user,name,icon,timestamp,img):
  self.tweet = tweet
  self.user = user
  self.name = name
  self.icon = icon
  self.timestamp = timestamp
  self.img = img
  
 def getTweet(self):
  return ([self.tweet, self.user, self.name, self.icon, self.timestamp, self.img])


# Configure printer
conn = cups.Connection()
printers = conn.getPrinters()
printer_name = printers.keys()[0]
conn.cancelAllJobs(printer_name)
conn.enablePrinter(printer_name)


# function to print wrapped text nicely
def drawText(surface, text, color, rect, font, aa=True, bkg=None):
 rect = pg.Rect(rect)
 y = rect.top
 lineSpacing = -2
 
 # get the height of the font
 fontHeight = font.size("Tg")[1]
 
 while text:
  i = 1
 
  # determine if the row of text will be outside our area
  if y + fontHeight > rect.bottom:
   break
 
  # determine maximum width of line
  while font.size(text[:i])[0] < rect.width and i < len(text):
   i += 1
 
  # if we've wrapped the text, then adjust the wrap to the last word      
  if i < len(text): 
   i = text.rfind(" ", 0, i) + 1
 
  # render the line and blit it to the surface
  if bkg:
   image = font.render(text[:i], 1, color, bkg)
   image.set_colorkey(bkg)
  else:
   image = font.render(text[:i], aa, color)
 
   surface.blit(image, (rect.left, y))
   y += fontHeight + lineSpacing
 
   # remove the text we just blitted
   text = text[i:]
 
 return text


# set up the screen
pg.init()
screen = pg.display.set_mode((scrWidth, scrHeight), pg.FULLSCREEN)
screen.fill(emfPurple)
pg.mouse.set_visible(False)

# set up fonts
bigFont = pg.font.Font("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 28)
smallFont = pg.font.Font("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 24)
tinyFont = pg.font.Font("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 16)

# Display IP address at start
text = smallFont.render("IP address = "+ip, True, white, emfPurple)
screen.blit(text,(80,1600))

pg.display.flip()
time.sleep(5)

# Clear screen and get ready for tweeting
screen.fill(emfPurple)
pg.display.flip()

# footer text and logo
text = bigFont.render("Searching for tweets mentioning '"+filter+"'", True, white, emfPurple)
screen.blit(text, (80,1550))

img=pg.image.load('emfLogo.png')
screen.blit(img,(755,1550))

pg.display.flip()


# class to deal with new tweets and display them
class listener(StreamListener):
 def on_data(self,data):
  global tweetList
  
  all_data=json.loads(data)
  tweetText=all_data["text"]
  
   # strip unicode from tweet
  unicode = re.compile(u'[^\u0000-\uD7FF\uE000-\uFFFF]', re.UNICODE)
  tweetText = unicode.sub(u'\uFFFD', tweetText)
  
  try:
   if (all_data['entities']['media'][0]['type']=='photo'):
    tweetList.appendleft(tweet(tweetText, "@"+all_data["user"]["screen_name"], all_data["user"]["name"], all_data["user"]["profile_image_url"], all_data["created_at"], all_data['entities']['media'][0]['media_url'] ))
  except:
   tweetList.appendleft(tweet(tweetText, "@"+all_data["user"]["screen_name"], all_data["user"]["name"], all_data["user"]["profile_image_url"], all_data["created_at"],0 ))
  
  if (debug):
   pp = pprint.PrettyPrinter(indent=3)
   print "######################################"
   for i in range(0, len(tweetList)):
    #print tweetList[i].getTweet()
    print "> "+str(i)
    pp.pprint(tweetList[i].getTweet())
    print " "
  
  ##### UPDATE FOOTER #####
  # status text
  text = smallFont.render("Last tweet at "+str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')), True, white, emfPurple)
  pg.draw.rect(screen,emfPurple,(80,1585,text.get_width()+100,text.get_height()),0) # background
  screen.blit(text, (80,1585))

  text = smallFont.render("Status: OK", True, green, emfPurple)
  pg.draw.rect(screen,emfPurple,(80,1615,890,text.get_height()),0) # background
  screen.blit(text, (80,1615))
  
  img=pg.image.load('emfLogo.png')
  screen.blit(img,(755,1550))

  ##### GENERATE ON-SCREEN LIST OF TWEETS #####
  # Draw 6 boxes down the screen, 80px margin L&R, 40px top
  # Each box 890 x 200px
  
  # Clear the entire tweet region of the screen
  pg.draw.rect(screen,emfPurple,(0,0,1050,1540),0)
  
  for boxCount in xrange(0,len(tweetList),1):
   y = 40 + ((boxCount)*240)
   
   # main box
   pg.draw.rect(screen,emfPurple,(80,y,890,200),0)
   pg.draw.rect(screen,white,(80,y,890,200),1) 
   
   # icon
   iconUrl=tweetList[boxCount].icon.replace('_normal', '_bigger')
   try:
    iconStr=urlopen(iconUrl).read()
    iconFile=io.BytesIO(iconStr)
    icon=pg.image.load(iconFile)
    screen.blit(icon,(95,y+15))
   except:
    pg.draw.rect(screen,white,(95,y+15,73,73),1)
   
   # username
   text = bigFont.render(tweetList[boxCount].user+": "+tweetList[boxCount].name, True, white, emfPurple)
   screen.blit(text, (184,y+17))
   
   # tweet
   if (tweetList[boxCount].img==0):
    rect = pg.Rect((182,y+56,773,150))
    drawText(screen, tweetList[boxCount].tweet, white, rect, smallFont)
   else:
    rect = pg.Rect((182,y+56,525,150))
    drawText(screen, tweetList[boxCount].tweet, white, rect, smallFont)
    
   # timestamp
   #print tweetList[boxCount].timestamp
   timestamp = tweetTime(tweetList[boxCount].timestamp)
   text = tinyFont.render(timestamp, True, white, emfPurple)
   screen.blit(text,(95,y+170))
   
   # image
   if (tweetList[boxCount].img!=0):
    #pg.draw.rect(screen,white,(705,y+15,250,170),1)
    try:
     photoUrl=tweetList[boxCount].img
     photoStr=urlopen(photoUrl+":small").read()
     photoFile=io.BytesIO(photoStr)
     photo=pg.image.load(photoFile)
     
     photoW,photoH=photo.get_rect().size
     
     # Check if image is too high (> 170px) and resize, maintaining ratio
     if(photoH > 170): # resize the image to fit
      photo = pg.transform.smoothscale(photo,(photoW/(photoH/170),170))
     
     photoW,photoH=photo.get_rect().size
     
     if(photoW > 250):
      chopPixels=int((photoW-250)/2)
      screen.blit(photo,(705,y+15),(chopPixels,0,250,170))
     else: 
      screen.blit(photo,(705+(250-photoW),y+15,250,170))
    except:
     print sys.exc_info()
     pass
      
  
  pg.display.flip()
 
  #for event in pg.event.get():
  # if event.type == pg.QUIT:
  #  pg.quit()
  #  raise SystemExit
  # if (event.type is pg.MOUSEBUTTONDOWN):
  #  sys.exit()

  ##### PRINTING #####

  if (printing and boxCount==5):
   # Print the tweet
   
   if (tweetList[boxCount].img!=0):
    printHeight=370
    printWidth=370
   else:
    printHeight=200
    printWidth=370
   
   printImg = Image.new("RGB", (printWidth,printHeight), white)
   
   draw = ImageDraw.Draw(printImg)
   draw.rectangle([1,1,printWidth-1,printHeight-1], fill="black", outline="black")
   draw.rectangle([3,3,printWidth-3,printHeight-3], fill="white", outline="black")
   
   # Username
   draw.font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 40)
   w, h = draw.textsize(tweetList[boxCount].user)
   x = printWidth-(w/2)
   y = printHeight-(h/2)
   
   userText = tweetList[boxCount].user
   draw.text((4,2), userText, black)
   
   # Tweet
   draw.font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 20)
   offset=0
   tweetText = tweetList[boxCount].tweet
   
   for line in (textwrap.wrap(tweetText, width=40)): 
    draw.text((4,50+offset), line, black)
    offset+=draw.textsize(tweetText)[1]
   
   # Time
   draw.font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeSans.ttf", 17)
   w, h = draw.textsize(tweetTime(tweetList[boxCount].timestamp))
   x = printWidth-(w/2)
   y = printHeight-(h/2)
   
   userText = tweetTime(tweetList[boxCount].timestamp)
   draw.text((4,(printHeight-h)-6), userText, black)
   
   # Image
   if (tweetList[boxCount].img!=0): 
    printPhoto = Image.frombytes("RGBA", photo.get_rect().size, pg.image.tostring(photo, "RGBA", False))
    printPhoto.thumbnail((360,170), Image.ANTIALIAS)
    #printPhoto = printPhoto.resize((250, (370/printPhoto.size[1])*printPhoto.size[0]),Image.ANTIALIAS)
    if (printPhoto.size[0] > 360):
     # Crop the image width
     printPhotoW = printPhoto.size[0]
     printPhotoH = printPhoto.size[1]
     printPhotoCrop = 360-printPhotoW
     printPhoto.crop((0, printPhotoCrop, printPhotoH, printPhotoW-printPhotoCrop))
    
    printPhotoW = printPhoto.size[0]
    printImg.paste(printPhoto,(int((360-printPhotoW)/2),180))
    
   printImg.save('/tmp/tweet.bmp')
 
   if (tweetList[boxCount].img!=0): 
    conn.printFile(printer_name, '/tmp/tweet.bmp', 'tweet', {'orientation-requested':'3', 'print-color-mode-default':'monochrome', 'media':'om_x-52-mmy-60-mm_51.86x59.97mm'})
   else:
     conn.printFile(printer_name, '/tmp/tweet.bmp', 'tweet', {'orientation-requested':'3', 'print-color-mode-default':'monochrome'})
     
   if (cutPaper):
    # cut paper
    with open('/dev/usb/lp0', 'wb') as f:
     f.write(b'\x1B\x6D')
    f.close()

 def on_error(self,status):
  #timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  #print timestamp+" - Error: "+str(status)
  print str(status)
  text = smallFont.render("Error: "+status, True, red, emfPurple)
  pg.draw.rect(screen,emfPurple,(80,1615,890,text.get_height()),0) # background
  pg.draw.rect(screen,emfPurple,(80,15,text.get_width()+100,text.get_height()),0) # background
  screen.blit(text, (80,1615))



  #sys.exit()

if __name__ == '__main__':
  try:
   auth = OAuthHandler(ckey,csecret)
   auth.set_access_token(atoken, asecret)

   twitterStream = Stream(auth, listener())
   twitterStream.filter(track=[filter])

  except KeyboardInterrupt:
   twitterStream.disconnect()
   sys.exit()

  #except Exception as e:
  # info = str(e)
  # sys.stderr.write("Unexpected exception. %s\n"%(info))
  # print sys.exc_info()[-1].tb_lineno
  # sys.exit()
