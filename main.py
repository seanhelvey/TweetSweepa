
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext.db import djangoforms
import urllib2
import tweetDB
import cgitb
cgitb.enable()

class Hack(djangoforms.ModelForm):
    class Meta:
        model = tweetDB.Hack

class FrontPage(webapp.RequestHandler):
    def get(self):

        q = db.GqlQuery("SELECT * FROM Hack")
        results = q.fetch(10)
        for result in results:
            result.delete()

        html = '<html><head><title>TweetSweepa</title></head><body>'
        html = html + "<h3>Welcome to the TweetSweepa!<br></h3>"
        html = html + "<h4>Search for the following words:<br></h4>"
        html = html + '<div id="wrapper">'
        html = html + '<form method="POST" action="/">'
        html = html + str(Hack(auto_id=False))
        html = html + '<input type="submit" name="sub_title" value="Submit">'        
        html = html + '</form>'
        html = html + '</div>'
        html = html + '</body></html>'
        self.response.out.write(html)

    def post(self):
        page = tweetDB.Hack()
        page.textBox1 = self.request.get('textBox1')
        page.textBox2 = self.request.get('textBox2')
        page.put()

        html = '<html><head><title>TweetSweepa</title></head><body>'
        html = html + '<a href="/results">results</a>'
        html = html + '</body></html>'
        self.response.out.write(html)
        
class ResultsPage(webapp.RequestHandler):    
    def get(self):

        a = db.GqlQuery("SELECT * FROM Hack")
        results = a.fetch(10)
        for result in results:
            var1 = result.textBox1
            var2 = result.textBox2

        url = 'http://search.twitter.com/search.json?q=' + var1 + '%20' + var2 + '&r\
pp=5&include_entities=true&result_type=mixed'

        req = urllib2.urlopen(url)
        text = str(req.read())
        results = text.index('[')
        meat = text[results:len(text)]
        chunks = meat.split('"created_at"')

        allTweets = []
        for chunk in chunks:
            if "text" in chunk:
                tweets = chunk.split('},{')
                for tweet in tweets:
                    allTweets.append(tweet)

        cleanTweets = []
        for tweet in allTweets:
            subStrBeg = tweet.find('","text":')
            if subStrBeg != -1:
                cleanTweets.append(tweet[subStrBeg+10:])

        html = '<html><head><title>Results</title></head><body>'

        for clean in cleanTweets:
            subStrEnd = clean.find('","')
            peice = clean[:subStrEnd]

            html = html + peice + '<br>'
            
        html = html + '</body></html>'
        self.response.out.write(html)

application = webapp.WSGIApplication([('/', FrontPage),('/results',ResultsPage)],debug=True)

def main():
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()
