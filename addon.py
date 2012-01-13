# -*- coding: utf-8 -*-

# Debug
Debug = False

# Imports
import sys, os, re, string, urllib, urllib2, simplejson, feedparser, shelve
import md5, os, shutil, tempfile, time, errno
import xbmc, xbmcgui, xbmcplugin, xbmcaddon

__addon__ = xbmcaddon.Addon(id='plugin.video.miro')
__info__ = __addon__.getAddonInfo
__plugin__ = __info__('name')
__version__ = __info__('version')
__icon__ = __info__('icon')
__fanart__ = __info__('fanart')
__path__ = __info__('path')
__cachedir__ = __info__('profile')
__language__ = __addon__.getLocalizedString
__settings__ = __addon__.getSetting

CACHE_1MINUTE = 60
CACHE_1HOUR = 3600
CACHE_1DAY = 86400
CACHE_1WEEK = 604800
CACHE_1MONTH = 2592000

CACHE_TIME = CACHE_1HOUR

MIRO_URL = 'http://www.miroguide.com/'
MIRO_API = 'https://www.miroguide.com/api/'

# Fanart
xbmcplugin.setPluginFanart(int(sys.argv[1]), __fanart__)

class Main:
  def __init__(self):
    if ("action=playyoutubevideo" in sys.argv[2]):
      self.PlayYouTubeVideo()
    elif ("action=categories" in sys.argv[2]):
      self.Categories()
    elif ("action=getdirectory" in sys.argv[2]):
      self.GetDirectory(self.Arguments('filter'), self.Arguments('title'))
    elif ("action=getfeed" in sys.argv[2]):
      self.GetFeed(self.Arguments('url', True))
    elif ("action=getmirofeed" in sys.argv[2]):
      self.GetMiroFeed(self.Arguments('url', True))
    elif ("action=subscribe" in sys.argv[2]):
      self._subscribe(self.Arguments('key'),
                      self.Arguments('name', True),
                      self.Arguments('feedurl', True),
                      self.Arguments('thumbnail_url'),
                      self.Arguments('description',))
      self._notification('Subscribe', 'Feed added to My Subscriptions!')
    elif ("action=unsubscribe" in sys.argv[2]):
      self._unsubscribe(self.Arguments('key', False))
      self._notification('UnSubscribe', 'Feed deleted from My Subscriptions!')
    elif ("action=mysubscription" in sys.argv[2]):
      self.GetSubscriptions()
    else:
      self.START()

  def START(self):
    if Debug: self.LOG('DEBUG: START()')
    category = []
    # If there is miro.db show My Subscription directory.
    if os.path.isfile(xbmc.translatePath(__cachedir__ + '/miro.db')):
      s = shelve.open(xbmc.translatePath(__cachedir__) + '/miro.db', protocol=2)
      if s.keys() != []:
        if Debug: self.LOG('DEBUG: My Subscriptions directory activated.')
        s.close()
        category += [{'title':'[B]My Subscriptions[/B]', 'url':'', 'action':'mysubscriptions'}]
    category += [{'title':'Categories', 'url':'https://www.miroguide.com/api/list_categories?datatype=json', 'action':'categories'},
                 {'title':'Languages', 'url':'https://www.miroguide.com/api/list_languages?datatype=json', 'action':'categories'},
                 {'title':'New Channels', 'url':'http://feeds.feedburner.com/miroguide/new', 'action':'getmirofeed'},
                 {'title':'Featured Channels', 'url':'http://feeds.feedburner.com/miroguide/featured', 'action':'getmirofeed'},
                 {'title':'Popular Channels', 'url':'http://feeds.feedburner.com/miroguide/popular', 'action':'getmirofeed'},
                 {'title':'Top Rated Channels', 'url':'http://feeds.feedburner.com/miroguide/toprated', 'action':'getmirofeed'},
                 {'title':'HD Channels', 'url':'https://www.miroguide.com/rss/tags/HD', 'action':'getmirofeed'},
                 #{'title':'Search for Feed...', 'url':'https://www.miroguide.com/rss/search/', 'action':'getmirofeed'},
                 ]
    for i in category:
      listitem = xbmcgui.ListItem(i['title'], iconImage='DefaultFolder.png', thumbnailImage=__icon__)
      parameters = '%s?action=%s&url=%s&title=%s' % (sys.argv[0], i['action'], urllib.quote_plus(i['url']), i['title'])
      xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(parameters, listitem, True)])
    # Sort methods and content type...
    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_NONE)
    # End of directory...
    xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

  def GetSubscriptions(self):
    if Debug: self.LOG('DEBUG: GetSubscriptions()')
    s = shelve.open(xbmc.translatePath(__cachedir__) + '/miro.db', protocol=2)
    for k, v in s.iteritems():
      id = k
      name = v['name']
      feedUrl = v['url']
      if not feedUrl: continue
      try: thumb = v['thumbnail_url']
      except: pass
      summary = v['description']
      listitem = xbmcgui.ListItem(name, iconImage='DefaultVideo.png', thumbnailImage=thumb)
      listitem.setInfo(type='video',
                       infoLabels={'title' : name,
                                   'plot' : summary,
                                   })
      contextmenu = [('UnSubscription', 'XBMC.RunPlugin(%s?action=unsubscribe&key=%s)' % \
                                                       (sys.argv[0], id))]
      listitem.addContextMenuItems(contextmenu, replaceItems=False)
      parameters = '%s?action=getfeed&url=%s' % (sys.argv[0], urllib.quote_plus(feedUrl))
      xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(parameters, listitem, True)])
    s.close()
    # Sort methods and content type...
    xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
    # End of directory...
    xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

  def Categories(self):
    if Debug: self.LOG('DEBUG: Categories()')
    categories = simplejson.loads(fetcher.fetch(self.Arguments('url', True), CACHE_TIME))
    if self.Arguments('title') == 'Categories':
      filter = 'category'
    else: filter = 'language'
    for category in categories:
      title = category['name']
      listitem = xbmcgui.ListItem(title, iconImage='DefaultFolder.png', thumbnailImage=__icon__)
      parameters = '%s?action=getdirectory&title=%s&filter=%s' % (sys.argv[0], urllib.quote_plus(title), filter)
      xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(parameters, listitem, True)])
    # Sort methods and content type...
    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_NONE)
    # End of directory...
    xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

  def GetDirectory(self, filter, title, sort='popular'):
    if Debug: self.LOG('DEBUG: GetDirectory()')
    # for next page
    try:
      offset = int(self.Arguments('offset')) + 20
    except:
      offset = 0
    url = MIRO_API + 'get_channels?datatype=json&filter=%s&filter_value=%s&sort=%s&offset=%s' % (filter, title, sort, offset)
    results = simplejson.loads(fetcher.fetch(url, CACHE_TIME))
    totalitem = len([i['id'] for i in results])
    for entry in results:
      id = entry['id']
      name = entry['name'].encode('utf-8', 'replace')
      publisher = entry['publisher']
      feedUrl = entry['url']
      if not feedUrl: continue
      if not len(entry['item']): continue
      try: thumb = entry['thumbnail_url']
      except: pass
      summary = entry['description']
      subscribe_hit_url = entry['subscribe_hit_url']
      subscription_count = entry['subscription_count']
      hi_def = entry['hi_def']
      average_rating = entry['average_rating']
      listitem = xbmcgui.ListItem(name, iconImage='DefaultVideo.png', thumbnailImage=thumb)
      if self._issubscripted(id):
        overlay = xbmcgui.ICON_OVERLAY_WATCHED
        contextmenu = [('UnSubscription', 'XBMC.RunPlugin(%s?action=unsubscribe&key=%s)' % \
                                                         (sys.argv[0], id))]
      else:
        overlay = xbmcgui.ICON_OVERLAY_NONE
        contextmenu = [('Subscribe', 'XBMC.RunPlugin(%s?action=subscribe&key=%s&name=%s&feedurl=%s&thumbnail_url=%s&description=%s)' % \
                                                    (sys.argv[0], id, urllib.quote_plus(name), urllib.quote_plus(feedUrl), thumb, summary))]
      listitem.setInfo(type='video',
                       infoLabels={'title' : name,
                                   'plot' : summary,
                                   'director' : publisher,
                                   'overlay' : overlay
                                   })
      listitem.addContextMenuItems(contextmenu, replaceItems=False)
      parameters = '%s?action=getfeed&url=%s' % (sys.argv[0], urllib.quote_plus(feedUrl))
      xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(parameters, listitem, True)])
    # Next Page
    # If less then 20 we are end of the list. No need next page.
    if not totalitem < 20:
      listitem = xbmcgui.ListItem('Next Page >>', iconImage='DefaultVideo.png', thumbnailImage=__icon__)
      parameters = '%s?action=getdirectory&title=%s&filter=%s&offset=%i' % \
                    (sys.argv[0], title, filter, offset)
      xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(parameters, listitem, True)])
    # Sort methods and content type...
    xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
    #xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_MPAA_RATING)
    #xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_RATING)
    # End of directory...
    xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

  def GetMiroFeed(self, url):
    if Debug: self.LOG('DEBUG: GetMiroFeed()')
    feedHtml = fetcher.fetch(url, CACHE_TIME)
    encoding = feedHtml.split('encoding="')[1].split('"')[0]
    feedHtml = feedHtml.decode(encoding, 'ignore').encode('utf-8')

    feed = feedparser.parse(feedHtml)
    for item in feed['items']:
      infoLabels = {}
      if item.link.startswith('http://www.miroguide.com/feeds/'):
        id = item.link.replace('http://www.miroguide.com/feeds/', '')
      else:
        id = re.findall('/(.+?).jpeg', item.thumbnail)[0]
      title = infoLabels['title'] = item.title.replace('&#39;', "'").replace('&amp;', '&').replace('&quot;', '"')
      if isinstance(title, str): # BAD: Not true for Unicode strings!
        try:
          title = infoLabels['title'] = title.encode('utf-8', 'replace') #.encode('utf-8')
        except:
          continue #skip this, it likely will bork
      # I put it here because above isinstance code not working well with some languages.
      title = infoLabels['title'] = title.encode('utf-8', 'replace') #.encode('utf-8')
      try:
        infoLabels['date'] = item.updated
      except:
        infoLabels['date'] = ''
      subtitle = infoLabels['date']
      soup = self.StripTags(item.description)#, convertEntities=BSS.HTML_ENTITIES
      try:
        infoLabels['plot'] = soup.contents[0]
      except:
        infoLabels['plot'] = item.description.encode('utf-8', 'ignore')
      thumb = item.thumbnail
      if thumb == '':
          thumb = __icon__
      feedUrl = item["summary_detail"]["value"].replace('amp;', '')
      feedUrl = feedUrl[feedUrl.find('url1=') + 5:]
      feedUrl = feedUrl[:feedUrl.find('&trackback1')].replace('%3A', ':')
      feddUrl = feedUrl.replace(' ', '%20')

      listitem = xbmcgui.ListItem(title, iconImage='DefaultVideo.png', thumbnailImage=thumb)
      if self._issubscripted(id):
        infoLabels['overlay'] = xbmcgui.ICON_OVERLAY_WATCHED
        contextmenu = [('UnSubscription', 'XBMC.RunPlugin(%s?action=unsubscribe&key=%s)' % \
                                                         (sys.argv[0], id))]
      else:
        infoLabels['overlay'] = xbmcgui.ICON_OVERLAY_NONE
        contextmenu = [('Subscribe', 'XBMC.RunPlugin(%s?action=subscribe&key=%s&name=%s&feedurl=%s&thumbnail_url=%s&description=%s)' % \
                                                    (sys.argv[0], id, urllib.quote_plus(title), urllib.quote_plus(feedUrl), thumb, ''))]
      listitem.setInfo(type='video', infoLabels=infoLabels)
      listitem.addContextMenuItems(contextmenu, replaceItems=False)
      parameters = '%s?action=getfeed&url=%s' % (sys.argv[0], urllib.quote_plus(feedUrl))
      xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(parameters, listitem, True)])
    # Sort methods and content type...
    xbmcplugin.setContent(int(sys.argv[1]), 'movie')
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
    if infoLabels['date']:
      xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)
    # End of directory...
    xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

  def GetFeed(self, url):
    if Debug: self.LOG('DEBUG: GetFeed()')
    feedHtml = fetcher.fetch(url, CACHE_TIME)
    encoding = re.search(r"encoding=([\"'])([^\1]*?)\1", feedHtml).group(2) #'
    feedHtml = feedHtml.decode(encoding, 'ignore').encode('utf-8')

    feed = feedparser.parse(feedHtml)
    if 'items' in feed:
      items = feed['items']
    else: items = feed['entries']
    hasInvalidItems = False
    for item in items:
      infoLabels = {}
      infoLabels['duration'] = ''
      title = infoLabels['title'] = self.StripTags(item.title.replace('&#39;', "'").replace('&amp;', '&'))
      if isinstance(title, str): # BAD: Not true for Unicode strings!
        try:
          title = infoLabels['title'] = title.encode('utf-8', 'replace') #.encode('utf-8')
        except:
          continue #skip this, it likely will bork
      try:
        date_p = item.date_parsed
        infoLabels['date'] = time.strftime("%d.%m.%Y", date_p)
        #date = item.updated
      except:
        infoLabels['date'] = ''
      subtitle = infoLabels['date']
      soup = self.StripTags(item.description)#, convertEntities=BSS.HTML_ENTITIES
      if item.has_key('subtitle'):
        infoLabels['plot'] = item.subtitle
      else:
        try:
          infoLabels['plot'] = soup.contents[0]
        except:
          infoLabels['plot'] = item.description.encode('utf-8', 'ignore')
      try:
        thumb = item.media_thumbnail[0]['url']
      except:
        try:
          thumb = item.thumbnail
        except: thumb = ''
      key = ''
      if item.has_key('itunes_duration'):
        infoLabels['duration'] = item.itunes_duration
      if item.has_key('enclosures'):
        for enclosure in item["enclosures"]:
          key = enclosure['href']
          try:
            infoLabels['size'] = int(enclosure['length'])
          except:
            infoLabels['size'] = 0
      if key == '':
        key = item.link
      if key.count('.torrent') > 0:
        hasInvalidItems = True
        #insert message box re: not supporting torrents here.
        continue
      if key.count('.html') > 0:
        hasInvalidItems = True
        continue
      if key.count('youtube') > 0:
        if key.count('watch') == 0:
          key = 'http://www.youtube.com/watch?v=' + key.split('v/')[-1][:11] #http://www.youtube.com/v/hlkDIYxUrpA&amp;amp;hl=en&amp;amp;fs=1
          thumb = 'http://i.ytimg.com/vi/%s/default.jpg' % key.split("=")[-1]
          listitem_yt = xbmcgui.ListItem(title, iconImage='DefaultVideo.png', thumbnailImage=thumb)
          listitem_yt.setInfo(type='video', infoLabels=infoLabels)
          parameters = '%s?action=playyoutubevideo&url=%s' % (sys.argv[0], key)
          xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(parameters, listitem_yt, False)])
      if thumb == '':
          thumb = __icon__
      if hasInvalidItems:
        print ('Invalid items', 'No supported media types found.')
      listitem = xbmcgui.ListItem(title, iconImage='DefaultVideo.png', thumbnailImage=thumb)
      listitem.setInfo(type='video', infoLabels=infoLabels)
      listitem.setProperty('IsPlayable', 'true')
      xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(key, listitem, False)])
    # Sort methods and content type...
    xbmcplugin.setContent(int(sys.argv[1]), 'movies')
    if infoLabels['date']:
      xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
    if infoLabels['duration']:
      xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_RUNTIME)
    try:
      if infoLabels['size']:
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_SIZE)
    except:
      pass
    # End of directory...
    xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

  #TODO: Fix youtube play
  def PlayYouTubeVideo(sender, id):
    if Debug: self.LOG('DEBUG: PlayYouTubeVideo()')
    yt_page = HTTP.Request(id).content
    fmt_url_map = re.findall('"fmt_url_map".+?"([^"]+)', yt_page)[0]
    fmt_url_map = fmt_url_map.replace('\/', '/').split(',')

    fmts = []
    fmts_info = {}

    for f in fmt_url_map:
      (fmt, url) = f.split('|')
      fmts.append(fmt)
      fmts_info[str(fmt)] = url

    index = 0
    if YOUTUBE_FMT[index] in fmts:
      fmt = YOUTUBE_FMT[index]
    else:
      for i in reversed(range(0, index + 1)):
        if str(YOUTUBE_FMT[i]) in fmts:
          fmt = YOUTUBE_FMT[i]
          break
        else:
          fmt = 5

    url = fmts_info[str(fmt)]
    url = url.replace('\\u0026', '&')
    return Redirect(url)

  def StripTags(self, str):
    return re.sub(r'<[^<>]+>', '', str)

  def _subscribe(self, key, title, url, thumb, desc):
    if Debug: self.LOG('DEBUG: _subscribe()')
    s = shelve.open(xbmc.translatePath(__cachedir__) + '/miro.db', protocol=2)
    try:
      s[str(key)] = {'name' : title,
                     'url' : url,
                     'thumbnail_url': thumb,
                     'description' : desc}
    finally:
      s.close()

  def _unsubscribe(self, key):
    if Debug: self.LOG('DEBUG: _unubscribe()')
    s = shelve.open(xbmc.translatePath(__cachedir__) + '/miro.db', protocol=2)
    try:
      del s[str(key)]
    finally:
      s.close()

  def _issubscripted(self, key):
    if Debug: self.LOG('DEBUG: _issubscripted()')
    s = shelve.open(xbmc.translatePath(__cachedir__) + '/miro.db', protocol=2)
    if s.has_key(str(key)):
      return True
    else:
      return False
    s.close()

  def _notification(self, title, message):
    if Debug: self.LOG('DEBUG: _notification()\ntitle: %s\nmessage: %s' % (title, message))
    xbmc.executebuiltin("Notification(%s, %s, 6000)" % (title, message.encode('ascii', 'ignore')))

  def Arguments(self, arg, unquote=False):
    Arguments = dict(part.split('=') for part in sys.argv[2][1:].split('&'))
    if unquote:
      return urllib.unquote_plus(Arguments[arg])
    else:
      return Arguments[arg]

  def LOG(self, description):
    xbmc.log("[ADD-ON] '%s v%s': %s" % (__plugin__, __version__, description), xbmc.LOGNOTICE)

class DiskCacheFetcher:
  def __init__(self, cache_dir=None):
    # If no cache directory specified, use system temp directory
    if cache_dir is None:
      cache_dir = tempfile.gettempdir()
    if not os.path.exists(cache_dir):
      try:
        os.mkdir(cache_dir)
      except OSError, e:
        if e.errno == errno.EEXIST and os.path.isdir(cache_dir):
          # File exists, and it's a directory,
          # another process beat us to creating this dir, that's OK.
          pass
        else:
          # Our target dir is already a file, or different error,
          # relay the error!
          raise
    self.cache_dir = cache_dir

  def fetch(self, url, max_age=0):
    # Use MD5 hash of the URL as the filename
    filename = md5.new(url).hexdigest()
    filepath = os.path.join(self.cache_dir, filename)
    if os.path.exists(filepath):
      if int(time.time()) - os.path.getmtime(filepath) < max_age:
        if Debug: print 'File exists and reading from cache.'
        return open(filepath).read()
    # Retrieve over HTTP and cache, using rename to avoid collisions
    if Debug: print 'File not yet cached or cache time expired. File reading from URL and try to cache to disk'
    data = urllib2.urlopen(url).read()
    fd, temppath = tempfile.mkstemp()
    fp = os.fdopen(fd, 'w')
    fp.write(data)
    fp.close()
    shutil.move(temppath, filepath)
    return data

fetcher = DiskCacheFetcher(xbmc.translatePath(__cachedir__))

if __name__ == '__main__':
  Main()
