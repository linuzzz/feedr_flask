# -*- coding: utf-8 -*-

"""
    Feedr
    ~~~~~~

    A micro rss reader

    :copyright: (c) 2015 by Paolo C.
    :license: BSD.
"""

import os
import logging
import logging.handlers
import feedparser
from datetime import datetime
from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, jsonify


# app creation 
app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
   DATABASE=os.path.join(app.root_path, 'feedr.db'),
   DEBUG=True,
   SECRET_KEY='development key',
   EMAIL='admin@test.com',
   PASSWORD='default',
   LOG_FILENAME=os.path.join(app.root_path, 'feedr.log')
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

# Set up a specific logger with our desired output level
flogger = logging.getLogger('feedr')
flogger.setLevel(logging.DEBUG)

# Add the log message handler to the logger
handler = logging.handlers.RotatingFileHandler(app.config['LOG_FILENAME'], maxBytes=10000, backupCount=10)
handler.setLevel(logging.DEBUG)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

flogger.addHandler(handler)

flogger.info('Feedr start')
#flogger.debug('debug message')
#flogger.info('info message')
#flogger.warn('warn message')
#flogger.error('error message')
#flogger.critical('critical message')


#Connects to the specific database.
def connect_db():
   rv = sqlite3.connect(app.config['DATABASE'])
   rv.row_factory = sqlite3.Row
   return rv


#Initializes the database.
#To use this function a new schema.sql is required
#Just use it if the db is not already available
"""
def init_db():
   db = get_db()
   with app.open_resource('schema.sql', mode='r') as f:
      db.cursor().executescript(f.read())
   db.commit()
"""

"""
@app.cli.command('initdb')
def initdb_command():
   #Creates the database tables.
   init_db()
   print('Initialized the database.')
"""

#Opens a new database connection if there is none yet for the current application context.
def get_db():
   if not hasattr(g, 'sqlite_db'):
      g.sqlite_db = connect_db()
   return g.sqlite_db

#Closes the database again at the end of the request.
@app.teardown_appcontext
def close_db(error):
   if hasattr(g, 'sqlite_db'):
      g.sqlite_db.close()

'''
@app.route('/')
def show_entries():
   db = get_db()
   cur = db.execute('select title, summary from items')
   entries = cur.fetchall()
   return render_template('show_entries.html', entries=entries)
'''

@app.route('/')
def main():
   if not session.get('logged_in'):
      return redirect(url_for('login'))
   else:
      return redirect(url_for('menu'))


@app.route('/login', methods=['GET', 'POST'])
def login():
   error = None
   if request.method == 'POST':
      
      if request.form['email'] != app.config['EMAIL']:
         error = 'Invalid username'
      elif request.form['password'] != app.config['PASSWORD']:
         error = 'Invalid password'
      else:
         session['logged_in'] = True
         return redirect(url_for('main'))
   return render_template('login.html', e=error)
   
   
@app.route('/menu')
def menu():
   if not session.get('logged_in'):
      abort(401)
   db = get_db()
   cursor = db.execute('select * from categories where cat in (select distinct cat from sources)')
   folders = cursor.fetchall()
   
   return render_template('menu.html', f=folders, onlyMenu=True)
   

@app.route('/news/<cat>', methods=['GET'])
def news(cat):
   if not session.get('logged_in'):
     abort(401)
     
   limit = request.args.get('limit', 10, type=int)
      
   db = get_db()
   
   #prima richiesta per recuperare nuovamente l'indice delle categorie
   #questo perché non so come passare parametri tra request differenti
   #poi folders va nel render_template
   cur1 = db.execute('select * from categories where cat in (select distinct cat from sources)')
   folders = cur1.fetchall()   

   #option to see already red articles???   
   #deep need to better understand tuples!!!
   cur2 = db.execute('select sources.title as source, items.id, items.title, items.summary, items.content, items.favorite, items.read, items.url from items join sources on items.sourceid=sources.sourceid and sources.sourceid in (select sourceid from sources where cat = ?) and items.read=0 order by date(items.pubdate) desc limit ?', (cat,limit))
   items = cur2.fetchall()
         
   cur3 = db.execute('select count(items.id) from items join sources on items.sourceid=sources.sourceid and sources.sourceid in (select sourceid from sources where cat = ?) and items.read=0', (cat,))
   
   return render_template('menu.html', entries=items, f=folders, limit=limit, total=cur3.fetchone()[0], category=cat)
  

@app.route('/fav')
def fav():
   id = request.args.get('id', 0, type=int)
   flogger.info("fav on art: {}".format(id))
   
   if not session.get('logged_in'):
     abort(401)
   db = get_db()
   #in sqlite booleans are integers 0 and 1 and you can't use NOT to toggle values 
   db.execute('update items set favorite = abs(favorite - 1) where id = ?', (id,))
   db.commit()
   
   return jsonify(result="True")
   
   
@app.route('/getlogs')
def getlogs():
   if not session.get('logged_in'):
     abort(401)   
   f = open(app.config['LOG_FILENAME'], 'r')
   logs = ''
   for line in f:
      logs = logs + "<p>" + line + "</p>"
      
   return logs
   f.close   
   
   
#mark as read function   
@app.route('/mark')
def mark():
   id = request.args.get('id', 0, type=int)
   
   if not session.get('logged_in'):
     abort(401)
   db = get_db()
    
   db.execute('update items set read = 1 where id = ?', (id,))
   db.commit()
   
   return jsonify(result="True")
   
#mark all as read   
@app.route('/markall')
def markall():
   if not session.get('logged_in'):
      abort(401)
      
   db = get_db()
   
   #onlyonetime = True
   for i in request.args:
      id = request.args.get(i, '', type=str)
      db.execute('update items set read = 1 where id = ?', (id,))
      
      #la categoria dell'articolo non serve più perché il refresh lo faccio client-side via jquery, non devo ritornare indietro cat
      '''  
      if onlyonetime:
         cur = db.execute('select cat from sources where sourceid in (select sourceid from items where id = ?)', (id,))
         cat = cur.fetchone()[0]
         onlyonetime = False
      '''                           
   
   db.commit()
   #return redirect(url_for('news', cat=cat))
   #news(3)
   return jsonify(result="True")
   
@app.cli.command()
def refresh_cli(with_appcontext=False):
    #refresh articles from the command line
    #to use it with cron
    #[10:39:22 - paolo@~]$flask --app=bootapp refresh_cli
    flogger.info('Cli refreshing articles...')
    refresh(True)   

@app.route('/refresh', methods=['GET'])
def refresh(cli=False):
   #cli parameter allow to distinguish between function called in http context (via web) and cli command:
   #in cli context there is not logged in status...
   if not cli:
      if not session.get('logged_in'):
         abort(401)
         
   db = get_db()
   
   '''
   questo film per recuperare la data dell'ultimo insert non serve più, conviene usare etag e last-modified se presenti
   NON CANCELLARE QUESTO CODICE COMUNQUE
   ATTENZIONE ALLA QUERY PER RECUPERARE il timestamp dell'ultimo record inserito
   NOTARE che devo fare "order by datetime" non "order by date" se voglio ordinare per GIORNO ED ORA
   lastrecord = db.execute('select pubdate from items order by datetime(items.pubdate) desc limit 1')
   
   try:
      l = lastrecord.fetchone()[0]
      print "last:::::::::::::::: " 
      print l
      lastrecord_pythontime = datetime.strptime(l,"%Y-%m-%dT%H:%M")
      tdelta = datetime.now() - lastrecord_pythontime
      print "tdelta:::::::::::::::: " 
      print tdelta
   except:
      #se questa query non ritorna risultati significa che non ho items ovvero articoli
      print "No articles in db...inserting new ones..."    
	'''   
      
   flogger.info('Refreshing articles...') 
            
   cur = db.execute('select sourceid,title,url,etag,modified from sources')
   s = cur.fetchall()
   for sourceid,title,url,etag,modified in s:
      #bandwidth saving with etag and last-modified (http headers) 
      if etag != "":
      	feed = feedparser.parse(url, etag=etag)
      elif modified != "":
         feed = feedparser.parse(url, modified=modified)
      else:
      	feed = feedparser.parse(url)
      
      #feed status == 200 to load new items
      #feed status == 301 permanently moved
      if feed.has_key('status'):
      	if feed.status == 301:
      		flogger.warning("feed url permanently moved, please check new url:" + feed.href) 
      	elif feed.status != 200:
      	   flogger.debug("feed already loaded - {} - {} ".format(feed.href,feed.status))
      	   continue
      else:
         flogger.warning("Error loading source feed, please check url:" + feed.href)
      	      
      #update db sources with etag
      if feed.has_key('etag'):
      	cur4 = db.execute('update sources set etag = ? where sourceid = ?', [feed.etag, sourceid])
      	
      #update db sources with modified
      if feed.has_key('modified'):
      	cur5 = db.execute('update sources set modified = ? where sourceid = ?', [feed.modified, sourceid])
      
      for f in feed.entries:
         #alcuni feed non hanno url...li salto!
         if not f.has_key('link'):
         	continue
         
         #noooooooooo attenzione qui al fatto che per non avere un errore di binding devo mettere l'url con la tupla
         cur2 = db.execute('select url from items where url = ?', (f.link,))
         present = cur2.fetchone()
         
         #casino di dateformat nei feed rss di siti diversi
         
         #datetime in formato che sqlite gradisce
         if f.has_key('published_parsed'):         
            p = f.published_parsed
            pdate = datetime(p[0], p[1], p[2], p[3], p[4])
            pubDate = datetime.strftime(pdate,"%Y-%m-%dT%H:%M")
         elif f.has_key('updated_parsed'):
            p = f.updated_parsed
            pdate = datetime(p[0], p[1], p[2], p[3], p[4])
            pubDate = datetime.strftime(pdate,"%Y-%m-%dT%H:%M")
         else:
            pubDate = datetime.strftime(datetime.now(),"%Y-%m-%dT%H:%M")
         
         if present == None:
            flogger.debug("new article in db...published: {}".format(pubDate))
                                    
            mylist = []
            mylist.append(f.description)
            mylist.append(f.summary)
            try:
               mylist.append(f.content[0]['value'])
            except:
               mylist.append("")
            
            #prendo il testo più lungo tra summary, description, content perché i vari feed hanno comportamenti diversi a seconda del source
            contenuto = max(mylist, key=len)            
            
            db.execute('insert into items (sourceid, title, summary, content, favorite, read, url, pubdate) values (?, ?, ?, ?, ?, ?, ?, ?)', [sourceid, f.title, f.summary, contenuto, 0, 0, f.link, pubDate])
   
   db.commit()      
   
   #can't return True as bool because this func is called via jQuery.get requesting a string as return value      
   return "True"      
   

@app.route('/add', methods=['POST'])
def add_entry():
   if not session.get('logged_in'):
     abort(401)
   db = get_db()
   db.execute('insert into entries (title, text) values (?, ?)',
               [request.form['title'], request.form['text']])
   db.commit()
   flash('New entry was successfully posted')
   return redirect(url_for('show_entries'))


@app.route('/logout')
def logout():
   session.pop('logged_in', None)
   return redirect(url_for('main'))
