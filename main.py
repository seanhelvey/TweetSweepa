
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
import collections
import urllib2
from urllib2 import Request, urlopen, URLError
import tweetDB
import cgitb
cgitb.enable()
import sys

#-BEG-NLP--------------------------------------------------------------------------

import copy

trainingFile = "trainy.np"
developmentFile = "d.np"

class bigram(object):
    def __init__(self):
        self.priorWord = ''
        self.priorTag = ''
        self.currentWord = ''
        self.currentTag = ''
        self.nextTag = ''

        self.transition = ()
        self.emission = ()

        self.wordCount = 0
        self.tagCount = 0
        self.priorTagCount = 0
        self.transCount = 0
        self.emitCount = 0

        self.possTags = []

        self.transProb = 0
        self.emishProb = 0
        self.finalProb = 0
        
    def scoreCalc(self):
        self.transProb = self.transCount/float(self.priorTagCount)
        self.emishProb = self.emitCount/float(self.tagCount)
        self.finalProb = self.transProb * self.emishProb

class sentences(object):
    def __init__(self):
        self.list = []

        self.sentsMax = 0

    def addWord(self,gram):
        for sentence in self.list:
            sentence.bigrams.append(gram)

    def addSentence(self):
        sent = sentence()
        self.list.append(sent)
    
    def replicate(self,gram):

        holdList = []
        for s in self.list:
            c = sentence()
            c = copy.deepcopy(s)

            c.bigrams.pop()
            c.bigrams.append(gram)

            holdList.append(c)

        self.list = self.list[:] + holdList[:]

class sentence(object):
    def __init__(self):
        self.bigrams = []
        self.reverseBigrams = []
        self.score = 0
        self.max = 0
        
    def sentScore(self):
        switch = 0
        for gram in self.bigrams:
            if switch == 0:
                self.score = gram.finalProb
                switch = 1
            else:
                self.score = self.score * float(gram.finalProb)

#-END-NLP--------------------------------------------------------------------------

class Hack(djangoforms.ModelForm):
    class Meta:
        model = tweetDB.Hack
        exclude = ['newTag1','newTag2','newTag3','newTag4','newTag5']

class Tag(djangoforms.ModelForm):
    class Meta:
        model = tweetDB.Hack
        exclude = ['textBox1']

def search(string,letter):
    n = 0
    for i in range (len(string)):
        if string[i]==letter:
            n=n+1
            return True

class FrontPage(webapp.RequestHandler):

    def get(self):

        q = db.GqlQuery("SELECT * FROM Hack")
        results = q.fetch(10)
        for result in results:
            result.delete()

        html = '<html><head><title>TweetSweepa</title><link type="text/css" rel="stylesheet" href="/static/style.css" /></head><body>'
        html = html + "<p><h3>***UNDER CONSTRUCTION***</h3></p><br>"
        html = html + "<p><h3>Welcome to the TweetSweepa!</h3></p><br>"
        html = html + "<p>Search for the following words:</p><br>"
        html = html + '<div id="wrapper">'
        html = html + '<form method="POST" action="/">'
        html = html + '<p>' + str(Hack(auto_id=False))
        html = html + '<input type="submit" name="sub_title" value="Submit2">'        
        html = html + '</p></form>'
        html = html + '</div>'
        html = html + '</body></html>'
        self.response.out.write(html)

    def post(self):

        page = tweetDB.Hack()
        page.textBox1 = self.request.get('textBox1')
#        page.which_user = users.get_current_user()
        page.put()

        #CONTROL GOES HERE 
        #first post / second post

        if self.request.get('textBox1') != "":

        #-BEG-NLP----------------------------------------------------------------------------

            #open trainingFile for read
            file=open(trainingFile,'r')

        #list of bigrams for aggregating data
            theBigrams = []

        #dictionairies for counting
            wordDic = collections.defaultdict(int)
            tagDic = collections.defaultdict(int)
            transDic = collections.defaultdict(int)
            emitDic = collections.defaultdict(int)
            possDic1 = collections.defaultdict(list)
            possDic2 = collections.defaultdict(int)

        #last pos -> most likely pos
            lastDic = collections.defaultdict(str)

        #variables to store for the next iteration
            lastWord = ''
            lastTag = ''
            lastTagCount = 0


        #NEW LIST***
            listola = []


        #FIRST PASS~~~~~~
        #parsing input data
        #aggregating dictionairies
            file.seek(0)
            for line in file:
    
                gram = bigram()
                thisLine = line.split()
                listLen = len(thisLine)

            #assign PRIOR word and tag to gram
                gram.priorWord = lastWord
                gram.priorTag = lastTag
                gram.priorTagCount = lastTagCount

            #if the current line contains a word and a tag
                if listLen > 1:
        
                #assign CURRENT word and tag to gram
                    gram.currentWord = thisLine[0]
                    gram.currentTag = thisLine[1]
        
                #and add to dictionairy -> list
                    possDic1[gram.currentWord].append(gram.currentTag)
        
                else:
                    gram.currentWord = ''
                    gram.currentTag = ''

            #store transition & emission
                gram.transition = (gram.priorTag,gram.currentTag)
                gram.emission = (gram.currentTag,gram.currentWord)

            #increment dictionairies
                transDic[gram.transition] += 1
                emitDic[gram.emission] += 1
                wordDic[gram.currentWord] += 1
                tagDic[gram.currentTag] += 1
                possDic2[gram.currentWord] += 1
    
            #add the gram to our list
                theBigrams.append(gram)

            #set temp variables for next gram
                lastWord = gram.currentWord
                lastTag = gram.currentTag
                lastTagCount = gram.tagCount

        #Uniqify thingys in possDic1
            for thingy in possDic1:
                possDic1[thingy]=list(set(possDic1[thingy]))

            copyTagDic = copy.deepcopy(tagDic)
            copyTransDic = copy.deepcopy(transDic)

        #lastDic will have tag -> tag+1 in strings
            for tag in copyTagDic:
                lastDic[tag] = ""

        #Counting total transitions from tag
            for trans in transDic:
                copyTagDic[trans[0]] += 1

        #Taking transDic from count to prob
            for trans in transDic:
                copyTransDic[trans] = transDic[trans]/ float(copyTagDic[trans[0]])

        #Setting copyTagDic back to zero
            for tag in copyTagDic:
                copyTagDic[tag] = 0

        #Setting max
            for item in copyTransDic:
                if copyTagDic[item[0]] < copyTransDic[item]:
                    copyTagDic[item[0]] = copyTransDic[item]

        #Storing in lastDic
            for item in copyTransDic:
                if copyTagDic[item[0]] == copyTransDic[item]:

                #mapping tag -> tag + 1
                    lastDic[item[0]] = item[1]

            gramDic = collections.defaultdict(bigram)

        #COUNTING~~~~~~~~~~~~~
        #We want the data from the dictionairies
        #stored locally with each bigram object
            for item in theBigrams:

                item.wordCount = wordDic[item.currentWord]
                item.tagCount = tagDic[item.currentTag]
                item.priorTagCount = tagDic[item.priorTag]    
                item.transCount = transDic[item.transition]

                if item.emission[0] == item.currentTag and item.emission[1] == item.currentWord:
                    item.emitCount = emitDic[item.emission]

                item.possTags = possDic1[item.currentWord]

                item.scoreCalc()
                gramDic[(item.currentWord,item.currentTag)] = item

            #-END-NLP----------------------------------------------------------------------------
    
            a = db.GqlQuery("SELECT * FROM Hack")
            results = a.fetch(10)
            for result in results:
                var1 = result.textBox1
            
                splitted = var1.split(" ")
                z = len(var1.split(" "))
                if z == 1:
                    url = 'http://search.twitter.com/search.json?q=' + splitted[0] + '&rpp=5&include_entities=true&result_type=mixed'

                elif z == 2:
                    url = 'http://search.twitter.com/search.json?q=' + splitted[0] + '%20' + splitted[1] + '&rpp=5&include_entities=true&result_type=mixed'                 

                else:
                    url = 'http://search.twitter.com/search.json?q=' + splitted[0] + '%20' + splitted[1] + '%20' + splitted[2] + '&rpp=5&include_entities=true&result_type=mixed' 

            textile = ""
            dd = ""
            ddd = ""

            req = urllib2.urlopen(url)
            textile = str(req.read())
            results = textile.index('[')
            meat = textile[results:len(textile)]
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

#        html = '<html><head><title>Results</title></head><body>'
                
            atSignList = collections.defaultdict(int)
            hashTagList = collections.defaultdict(int)
            httpLinkList = collections.defaultdict(int)

            wordList = collections.defaultdict(int)
            for clean in cleanTweets:
                subStrEnd = clean.find('","')
                peice = clean[:subStrEnd]

#                html = html + peice + '<br>' + '<br>'

                words = peice.split(" ")

                #----------MODS--------------------------------
                sublist = []
                for word in words:

                   #~~~~~~~~~NEWNEW~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                
                    #search for @
                    foundAtSign = search(word,"@")
                    if foundAtSign == True:
                        atSignList[word] += 1

                    #search for #
                    foundHashTag = search(word,"#")
                    if foundHashTag == True:
                        hashTagList[word] += 1

                    #search for #
                    if "http" in word:
                        httpLinkList[word] += 1

                    #~~~~~~~~~NEWNEW~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

                    wordOne = ""
                    wordTwo = ""

                    word = word.replace("\\", "")

                    x = 0
                    x = word.find("\'")

                    if word[-1:] == "," or word[-1:] == "." or word[-2:] == ".." or word[-1:] == "!" or word[-1:] == "?" or word[-1:] == ":":
                        wordOne = word[:-1]
                        wordTwo = word[-1:]

                        if wordTwo == ",":
                            wordTwo = "COMMA"

                        wordList[wordOne] += 1
                        wordList[wordTwo] += 1
                
                        sublist.append(wordOne)

                        if wordTwo != "":
                            sublist.append(wordTwo) 

                    elif x > 0:

                        if word[x+1:] == "t":
                            wordOne = word[:x-1]
                            wordTwo = word[x-1:]

                        else:
                            wordOne = word[:x]
                            wordTwo = word[x:]

                        sublist.append(wordOne)
                        sublist.append(wordTwo)

                    else:
                        wordList[word] += 1                    
                        sublist.append(word)

                listola.append(sublist)

            #----------------------------------------------

        #-BEG-NLP--------------------------------------------------------------------
        
        #SECOND PASS~~~~~~~~
        #Building up lists of possible word combinations or "sentences"
        #Computing likelihood of each tag sequence

            file=open(developmentFile,'r')

            sentsList = []
            newSents = 1
            sentsListNum = 0
            theLastTag = ''
            oovList = collections.defaultdict(int)

#        self.response.out.write(listola)        
        
            for wordss in listola:

#            self.response.out.write(wordList)
            
                currentTag = ''

                if len(wordss) > 0:

                    for theWord in wordss:
                        if theWord != "COMMA":
                            theWordy = theWord.lower()
                        else:
                            theWordy = theWord

                        tags = possDic1[theWordy]

                        if newSents == 1:
                            newSents = 0
                            sents = sentences()
                            sents.addSentence()
    
                    #BIG CHANGE HERE ********************************
                        if len(tags) >= 1:

                            tagMax = 0

                            for tag in tags:
                                gram = gramDic[(theWordy,tag)]
                                currentTag = tag

                                if gram.finalProb >= tagMax:
                                    tagMax = gram.finalProb                    

                            for tag in tags:
                                gram = gramDic[(theWordy,tag)]
                
                                if gram.finalProb == tagMax:
                                    sents.addWord(gram)

                        else:
                        #self.response.out.write("oov: " + theWord + "<br>")

                            if theWord != "":
                                oovList[theWord] += 1

                            if len(tags) == 0:
                                gram = bigram()
                                gram.currentWord = theWord

                                if theLastTag != "" and lastDic[theLastTag] != "":
                                    gram.currentTag = lastDic[theLastTag]
                                else:
                                    gram.currentTag = "NN"
                                gram.finalProb = .0001
                                gramDic[(gram.currentWord,gram.currentTag)] = gram

                            else:
                                gram = gramDic[(theWord,tags[0])]
                                currentTag = tags[0]

                            sents.addWord(gram)

                    else:
                        newSents = 1
                        sentsList.append(sents)
                        sentsListNum = sentsListNum + 1

                    theLastTag = currentTag

#        self.response.out.write(listola)

        #Find max
            for sents in sentsList:
                for sent in sents.list:
                    sent.sentScore()
                    if sent.score > sents.sentsMax:
                        sents.sentsMax = sent.score

                    sent.reversedBigrams = reversed(sent.bigrams)
                    nextTag = ""
                    count = 0
                    for gram in sent.reversedBigrams:
                        if count != 0:
                            gram.nextTag = nextTag
                        nextTag = gram.currentTag
                        count += 1

        #outfile = open("out.txt","w")

            htmlc = '<html><head><title>Results</title><link type="text/css" rel="stylesheet" href="/static/style.css" /></head><body>'

            htmlc = htmlc + '<div id="left">'
            htmlc = htmlc + str(textile) + dd + ddd
            htmlc = htmlc + "<p>POS Tags - Out Of Vocabulary (OOV) in <span class='highlight'>red<span></p><br>"

        #Write output
            for sents in sentsList:
                num = 0

                htmlc = htmlc + "<p>"
        
                for sent in sents.list:
                    if sent.score == sents.sentsMax and num == 0:
                    
                        htmlc = htmlc + '<span class="sentence">'
                        for gram in sent.bigrams:
                            htmlc = htmlc + gram.currentWord + " "
                        htmlc = htmlc + '</span>'

                        htmlc = htmlc + "<br><br>"
                   
                        priorGramTag = ""

                        x = 0
                        for gram in sent.bigrams:
                            if gram.currentWord in oovList:

                                htmlc = htmlc + '<span class="highlight">'
                                htmlc = htmlc + str(gram.currentWord)
                                htmlc = htmlc + '</span>'

                                htmlc = htmlc + " [" +str(gram.currentTag) + "]<br>"

                            else:
                                htmlc = htmlc + str(gram.currentWord) + " [" + str(gram.currentTag) + "]<br>"

                            priorGramTag = gram.currentTag
                            x += 1
                            
                        num += 1

                    htmlc = htmlc + "</p><br><br>"

            htmlc = htmlc + "</div>"

#        htmlc = htmlc + '<div id="middleleft">'
#        htmlc = htmlc + "<h4>Out Of Vocab</h4><br>"
        
#        for x in oovList:
#            htmlc = htmlc + x + "<br>"
#        htmlc = htmlc + '</div>'

#        htmlc = htmlc + '<div id="middle">'
#        htmlc = htmlc + "<p>@ At Signs</p><br><p>"
        
#        for x in atSignList:
#            htmlc = htmlc + x + "<br>"
#        htmlc = htmlc + '</p></div>'

        #htmlc = htmlc + "\n"

            htmlc = htmlc + '<div id="top">'
            htmlc = htmlc + "<p>Active Learning / Domain Adaptation</p><br><p>"

            htmlc = htmlc + '<div id="wrapper">'

            #have been trying empty string & / for action
            htmlc = htmlc + '<form method="POST" action="/"><table>'
            htmlc = htmlc + str(Tag(auto_id=False))
            htmlc = htmlc + '<input type="submit" name="Submit" value="Submit">'        
            htmlc = htmlc + '</table></form>'
            htmlc = htmlc + '</div></p>'
            htmlc = htmlc + '</div>'

#        htmlc = htmlc + '<div id="right">'
#        htmlc = htmlc + "<p>URLs</p><br><p>"
        
#        for x in httpLinkList:
#            htmlc = htmlc + x + "<br>"
#        htmlc = htmlc + '</p></div>'

            htmlc = htmlc + '<div id="lexicon">'
            htmlc = htmlc + "<p>Words Added To Your Lexicon</p><br><p>"

            htmlc = htmlc + "Hello" + "<br>"

            htmlc = htmlc + '</p></div>'

            #htmlc = htmlc + '<a href="/results">Add To Lexicon</a>'

#        htmlc = htmlc + '<div id="oov">'
#        htmlc = htmlc + "<p>Active Learning</p><br><p>"
            htmlc = htmlc + '</body></html>'

            self.response.out.write(htmlc)

        else:

            htmlq = '<html><head><title>Results</title></head><body>'
            htmlq = htmlq + '<p><a href="/results">results</a></p>'
            htmlq = htmlq + '</body></html>'

            self.response.out.write(htmlq)

#~~~~~~~~~NEWNEW~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        
class ResultsPage(webapp.RequestHandler):    
    def get(self):

        htmlr = "<html><head><title>results</title></head><body>hi results</body></html>"

        self.response.out.write(htmlr)

        #-END-NLP--------------------------------------------------------------------


application = webapp.WSGIApplication([('/', FrontPage),('/results',ResultsPage)],debug=True)

def main():
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()
