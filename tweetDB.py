from google.appengine.ext import db

class Hack(db.Model):
    textBox1 = db.StringProperty()
    which_user = db.UserProperty()

class Tag(db.Model):
    newTag1 = db.StringProperty()
    newTag2 = db.StringProperty()
    newTag3 = db.StringProperty()
    newTag4 = db.StringProperty()
    newTag5 = db.StringProperty()
    which_user = db.UserProperty()

class NewWord(db.Model):
    name = db.StringProperty()
    one = db.StringProperty()
    two = db.StringProperty()
    three = db.StringProperty()
    four = db.StringProperty()
    five = db.StringProperty()
    score = db.StringProperty()

class Pair(db.Model):
    word = db.StringProperty()
    tag = db.StringProperty()
    which_user = db.UserProperty()

class Record(db.Model):
    score = db.StringProperty()
    word = db.StringProperty()
    which_user = db.UserProperty()    
