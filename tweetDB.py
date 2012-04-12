from google.appengine.ext import db

class Hack(db.Model):
    textBox1 = db.StringProperty()

class Fix(db.Model):
    textBox2 = db.StringProperty()
