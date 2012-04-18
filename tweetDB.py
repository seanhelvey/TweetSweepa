from google.appengine.ext import db

class Hack(db.Model):
    textBox1 = db.StringProperty()
    newTag1 = db.StringProperty()
    newTag2 = db.StringProperty()
    newTag3 = db.StringProperty()
    newTag4 = db.StringProperty()
    newTag5 = db.StringProperty()
#    which_user = db.UserProperty()
