from google.appengine.ext import db

class Hack(db.Model):
    textBox1 = db.StringProperty()
    which_user = db.UserProperty()

class Tag(db.Model):
    newTag1 = db.StringProperty(multiline=True)
    newTag2 = db.StringProperty(multiline=True)
    newTag3 = db.StringProperty(multiline=True)
    newTag4 = db.StringProperty(multiline=True)
    newTag5 = db.StringProperty(multiline=True)
    which_user = db.UserProperty()

class NewWord(db.Model):
    name = db.StringProperty()
    one = db.StringProperty(multiline=True)
    two = db.StringProperty(multiline=True)
    three = db.StringProperty(multiline=True)
    four = db.StringProperty(multiline=True)
    five = db.StringProperty(multiline=True)
    score = db.StringProperty(multiline=True)

class Pair(db.Model):
    word = db.StringProperty(multiline=True)
    tag = db.StringProperty(multiline=True)
    which_user = db.UserProperty()

class Record(db.Model):
    score = db.StringProperty(multiline=True)
    word = db.StringProperty(multiline=True)
    which_user = db.UserProperty()    
