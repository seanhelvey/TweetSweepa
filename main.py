
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
from urllib2 import Request, urlopen, HTTPError
import tweetDB
import cgitb
cgitb.enable()
import sys

from operator import itemgetter

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
        exclude = ['which_user']

class Tag(djangoforms.ModelForm):
    class Meta:
        model = tweetDB.Tag
        exclude = ['which_user']

class NewWord(djangoforms.ModelForm):
    class Meta:
        model = tweetDB.NewWord

class Pair(djangoforms.ModelForm):
    class Meta:
        model = tweetDB.Pair

class Record(djangoforms.ModelForm):
    class Meta:
        model = tweetDB.Pair

def search(string,letter):
    n = 0
    for i in range (len(string)):
        if string[i]==letter:
            n=n+1
            return True

def urlFun(self, url): 
    try:
        req = urllib2.urlopen(url)
        return req

    except HTTPError,e:
        htmlw = "<html><head><title>error</title></head><body>" + str(e) + "</body></html>"
        self.response.out.write(htmlw)

numWords = 0

class FrontPage(webapp.RequestHandler):

    def get(self):

        q = db.GqlQuery("SELECT * FROM Hack")
        results = q.fetch(3)
        for result in results:
            result.delete()

        qq = db.GqlQuery("SELECT * FROM Tag")
        results = qq.fetch(3)
        for result in results:
            result.delete()

        qqq = db.GqlQuery("SELECT * FROM NewWord")
        results = qqq.fetch(3)
        for result in results:
            result.delete()

        html = '<html><head><title>TweetSweepa</title><link type="text/css" rel="stylesheet" href="/static/style.css" /></head><body>'
        html = html + "<h4>***UNDER CONSTRUCTION***<br>"
        html = html + "Welcome to the TweetSweepa!<br>"
        html = html + "Search for the following words:</h4>"
        html = html + '<div id="wrapper">'
        html = html + '<form method="POST" action="/">'
        html = html + '<p>' + str(Hack(auto_id=False))
        html = html + '<input type="submit" name="sub_title" value="Submit2">'        
        html = html + '</p></form>'
        html = html + '</div><br><br>'
        html = html + 'To clear your user information, click the button below.<br>'
        html = html + 'This will remove your score record and refresh your lexicon.<br>'
        html = html + '<form method="POST" action="/">'
        html = html + '<input type="submit" name="sub_title" value="Clear">'
        html = html + '</body></html>'
        self.response.out.write(html)

    def post(self):

        q = db.GqlQuery("SELECT * FROM Hack")
        testResults = q.fetch(1)

        #CONTROL HERE 
        #first post / second post
        if self.request.get('textBox1') != "":

            page = tweetDB.Hack()
            page.textBox1 = self.request.get('textBox1')
            page.which_user = users.get_current_user()
            page.put()

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
            results = a.fetch(3)

            for result in results:
                var1 = result.textBox1
            
                splitted = var1.split(" ")
                z = len(var1.split(" "))
                if z == 1:
                    url = 'http://search.twitter.com/search.json?q=' + splitted[0] + '&rpp=80&include_entities=true&result_type=mixed&lang=en'

                elif z == 2:
                    url = 'http://search.twitter.com/search.json?q=' + splitted[0] + '%20' + splitted[1] + '&rpp=80&include_entities=true&result_type=mixed&lang=en'                 

                else:
                    url = 'http://search.twitter.com/search.json?q=' + splitted[0] + '%20' + splitted[1] + '%20' + splitted[2] + '&rpp=80&include_entities=true&result_type=mixed&lang=en' 

            textile = ""
            dd = ""
            ddd = ""

            req = urlFun(self,url)

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

            atSignList = collections.defaultdict(int)
            hashTagList = collections.defaultdict(int)
            httpLinkList = collections.defaultdict(int)

            wordList = collections.defaultdict(int)
            for clean in cleanTweets:
                subStrEnd = clean.find('","')
                peice = clean[:subStrEnd]

                words = peice.split(" ")

                #----------MODS--------------------------------
                sublist = []
                for word in words:

                    global numWords
                    numWords += 1

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

            qqq = db.GqlQuery("SELECT * FROM Pair")
            results = qqq.fetch(80)
            lexicon = collections.defaultdict(str)

            for wordss in listola:

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
                                                        
                            if len(tags) == 0:
                                gram = bigram()
                                gram.currentWord = theWordy

                                if theLastTag != "" and lastDic[theLastTag] != "":
                                    gram.currentTag = lastDic[theLastTag]
                                else:
                                    gram.currentTag = "NN"
                                gram.finalProb = .0001

                                #*****NEW
                                #search for @
                                foundAtSign = search(theWordy,"@")
                                foundHashTag = search(theWordy,"#")
                                
                                for result in results:
                                    if result.which_user == users.get_current_user():
                                        lexicon[result.word] = result.tag

                                if foundAtSign == True:
                                    gram.currentTag = "@"

                                #search for #
                                elif foundHashTag == True:
                                    gram.currentTag = "#"

                                #search for #
                                elif "http" in theWordy:
                                    gram.currentTag = "http"

                                #from theWord to theWordy below
                                else:
                                    if theWordy != "":

                                        if theWordy in lexicon:
                                            
                                            #dummy filler
                                            z = 7
                                            gram.currentTag = lexicon[theWordy]
                                        
                                        else:
                                            oovList[theWordy] += 1

                                    else:
                                        #dummy filler
                                        y = 3

                                gramDic[(gram.currentWord,gram.currentTag)] = gram

                            else:
                                gram = gramDic[(theWordy,tags[0])]
                                currentTag = tags[0]

                            sents.addWord(gram)

                    else:
                        newSents = 1
                        sentsList.append(sents)
                        sentsListNum = sentsListNum + 1

                    theLastTag = currentTag

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

            htmlc = '<html><head><title>Results</title><link type="text/css" rel="stylesheet" href="/static/style.css" /></head><body>'
            htmlc = htmlc + '<div id="left">'
            htmlc = htmlc + "<p>POS Tags - Out Of Vocabulary (OOV) in <span class='highlight'>red<span></p><br>"

            #Write output
            for sents in sentsList:
                num = 0

                htmlc = htmlc + "<p>"
        
                for sent in sents.list:
                    if sent.score == sents.sentsMax and num == 0:
                    
                        priorGramTag = ""

                        x = 0
                        for gram in sent.bigrams:
                            if gram.currentWord in oovList:

                                htmlc = htmlc + '<span class="highlight">'
                                htmlc = htmlc + str(gram.currentWord)
                                htmlc = htmlc + '</span>'

                                htmlc = htmlc + " [" +str(gram.currentTag) + "] "

                            else:
                                htmlc = htmlc + str(gram.currentWord) + " [" + str(gram.currentTag) + "] "

                            priorGramTag = gram.currentTag
                            x += 1
                            
                        num += 1

                    htmlc = htmlc + "</p><br><br>"

            htmlc = htmlc + "</div>"

            #oovList
            sortedList = sorted(oovList.items(), key=itemgetter(1))
            last5 = sortedList[-5:]
            last5.reverse()

            htmlc = htmlc + '<div id="top">'
            htmlc = htmlc + "<p>Active Learning / Domain Adaptation<br>"
            htmlc = htmlc + "The 5 most frequent oov words:<br></p>"

            htmlc = htmlc + '<div id="word1">'
            htmlc = htmlc + str(last5[0])
            htmlc = htmlc + '</div>'

            htmlc = htmlc + '<div id="word2">'
            htmlc = htmlc + str(last5[1])
            htmlc = htmlc + '</div>'

            htmlc = htmlc + '<div id="word3">'
            htmlc = htmlc + str(last5[2])
            htmlc = htmlc + '</div>'

            htmlc = htmlc + '<div id="word4">'
            htmlc = htmlc + str(last5[3])
            htmlc = htmlc + '</div>'

            htmlc = htmlc + '<div id="word5">'
            htmlc = htmlc + str(last5[4])
            htmlc = htmlc + '</div>'

            htmlc = htmlc + '<div id="wrapper">'

            #have been trying empty string & / for action
            htmlc = htmlc + '<form method="POST" action="/">'
            htmlc = htmlc + '<p>' + str(Tag(auto_id=False))
            htmlc = htmlc + '<input type="submit" name="Submit" value="Submit"></p>'
            htmlc = htmlc + '</form><br>'
            htmlc = htmlc + "PERCENTAGE IN VOCABULARY:"

            num = 0
            for oov in oovList:
                num += 1

            global numWords
            score = round((numWords-num)/float(numWords),4)*100
            htmlc = htmlc + str(numWords-num) + " / " + str(numWords) + " = " + str(score) + "%"

            newy = tweetDB.NewWord()
            newy.one = last5[0][0]
            newy.two = last5[1][0]
            newy.three = last5[2][0]
            newy.four = last5[3][0]
            newy.five = last5[4][0]
            newy.score = str(score)
            newy.put()

            #READING RECORDS HERE ***************
            
            zzzz = db.GqlQuery("SELECT * FROM Record")
            records = zzzz.fetch(10)

            htmlc = htmlc + "<br><br>"
            htmlc = htmlc + "PREVIOUS SCORES:<br>"
            for record in records:
                htmlc = htmlc + record.word + " " + record.score + "<br>"
            
            #***********************************

            htmlc = htmlc + '</div>'

            htmlc = htmlc + '</div>'

            htmlc = htmlc + '<div id="lexicon">'
            htmlc = htmlc + "<p>"+ str(page.which_user) + "'s Lexicon</p><br><p>"

#            qqq = db.GqlQuery("SELECT * FROM Pair")
#            results = qqq.fetch(50)

            for result in results:

                if result.which_user == users.get_current_user():
                    htmlc = htmlc + str(result.word) + " " + str(result.tag) + "<br>"

            htmlc = htmlc + '</p></div>'

            htmlc = htmlc + '</body></html>'

            self.response.out.write(htmlc)

        #else:
        elif self.request.get('textBox1') == "" and len(testResults) > 0:
            page = tweetDB.Tag()

            page.newTag1 = self.request.get('newTag1')
            page.newTag2 = self.request.get('newTag2')
            page.newTag3 = self.request.get('newTag3')
            page.newTag4 = self.request.get('newTag4')
            page.newTag5 = self.request.get('newTag5')

            page.which_user = users.get_current_user()
            page.put()

            #****************NEW
            q = db.GqlQuery("SELECT * FROM Hack")
            resultsX = q.fetch(3)
            for resultX in resultsX:
                searchString = resultX.textBox1
                user = resultX.which_user

            qq = db.GqlQuery("SELECT * FROM Tag")
            results = qq.fetch(3)
            for result in results:
                tag1 = result.newTag1
                tag2 = result.newTag2
                tag3 = result.newTag3
                tag4 = result.newTag4
                tag5 = result.newTag5
            
            qqq = db.GqlQuery("SELECT * FROM NewWord")
            results = qqq.fetch(3)
            for result in results:
                word1 = result.one
                word2 = result.two
                word3 = result.three
                word4 = result.four
                word5 = result.five
                score = result.score

            if tag1 != "":
                pair1 = tweetDB.Pair()
                pair1.word = word1
                pair1.tag = tag1
                pair1.which_user = user
                pair1.put()

            if tag2 != "":
                pair2 = tweetDB.Pair()
                pair2.word = word2
                pair2.tag = tag2
                pair2.which_user = user
                pair2.put()

            if tag3 != "":
                pair3 = tweetDB.Pair()
                pair3.word = word3
                pair3.tag = tag3
                pair3.which_user = user
                pair3.put()

            if tag4 != "":
                pair4 = tweetDB.Pair()
                pair4.word = word4
                pair4.tag = tag4
                pair4.which_user = user
                pair4.put()

            if tag5 != "":
                pair5 = tweetDB.Pair()
                pair5.word = word5
                pair5.tag = tag5
                pair5.which_user = user
                pair5.put()

            #WRITING RECORDS HERE ***************
                
            wreck = tweetDB.Record()
            wreck.which_user = user
            wreck.word = searchString

            wreck.score = str(score)

            wreck.put()
            
            #***********************************

            htmlq = '<html><head><title>Results</title></head><body>'
            htmlq = htmlq + '<p>The tags have been added to your lexicon! '
            htmlq = htmlq + '<a href="http://mznxbcv1029384756alskqpwo.appspot.com/">do it again</a></p>'
            htmlq = htmlq + '</body></html>'

            self.response.out.write(htmlq)

        else:
            
            #clear records
            #clear lexicon

            htmlq = '<html><head><title>Clear</title></head><body>'
            htmlq = htmlq + '<p>Your score record and lexicon have now been cleared! '
            htmlq = htmlq + '<a href="http://mznxbcv1029384756alskqpwo.appspot.com/">back to homepage</a></p>'
            htmlq = htmlq + '</body></html>'
            
            self.response.out.write(htmlq)
            
#~~~~~~~~~NEWNEW~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        
class ResultsPage(webapp.RequestHandler):    
    def get(self):

        htmlr = '<html><head><title>Results</title></head><body>'
        htmlr = htmlr + '<p><a href="/">The tags have been added to your lexicon!</a></p>'
        htmlr = htmlr + '</body></html>'

        self.response.out.write(htmlr)

        #-END-NLP--------------------------------------------------------------------

class ClearPage(webapp.RequestHandler):    
    def get(self):

        htmlr = '<html><head><title>Clear</title></head><body>'
        htmlr = htmlr + '<p><a href="/">Your score record and lexicon have been cleared.</a></p>'
        htmlr = htmlr + '</body></html>'

        self.response.out.write(htmlr)

application = webapp.WSGIApplication([('/', FrontPage),('/results',ResultsPage),('/clear',ClearPage)],debug=True)

def main():
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()
