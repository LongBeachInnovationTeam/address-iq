from flask import Flask
import flask.ext.assets
from flask.ext.sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_sslify import SSLify

app = Flask(__name__)
db = SQLAlchemy(app)
assets = flask.ext.assets.Environment()
sslify = SSLify(app)
mail = Mail(app)
