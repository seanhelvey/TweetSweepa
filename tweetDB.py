from google.appengine.ext import db

class Hack(db.Model):
    textBox1 = db.StringProperty()
    newTag = db.StringProperty()
