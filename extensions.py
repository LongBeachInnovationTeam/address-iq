from flask import Flask
import flask.ext.assets
from flask.ext.login import LoginManager
from flask.ext.sqlalchemy import SQLAlchemy
from flask_sslify import SSLify

app = Flask(__name__)
db = SQLAlchemy(app)
login_manager = LoginManager()
assets = flask.ext.assets.Environment()
sslify = SSLify(app)
mail = Mail(app)
