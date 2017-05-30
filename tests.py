from extensions import app, db
from app import fetch_incidents_at_address, count_incidents_by_timeframes, get_top_incident_reasons_by_timeframes
from count_calls_for_service import count_calls
from factories import FireIncidentFactory, StandardizedFireIncidentFactory, PoliceIncidentFactory, StandardizedPoliceIncidentFactory, BusinessLicenseFactory, UserFactory
from flask.ext.login import login_user
from httmock import response, HTTMock
from requests.auth import HTTPBasicAuth
import base64
import datetime
import mock
import models
import os
import pytz
import requests
import unittest

os.environ['APP_SETTINGS'] = 'config.TestingConfig'

login_test_username = 'Alex.Chavez@longbeach.gov'
login_test_password = 'hunter2'

def get_date_days_ago(days):
    return datetime.datetime.now() - datetime.timedelta(days=days)

class HomeTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()

    def tearDown(self):
        pass

    def testHomePageReturns200(self):
        rv = self.app.get('/')
        assert rv.status_code == 200

class LoginTestCase(unittest.TestCase):

    # @todo: Integrate this with others, probably, so you confirm that access
    # control is as it should be throughout.

    def setUp(self):
        self.app = app.test_client()
        # db.create_all()

    def tearDown(self):
        # db.drop_all()
        pass

    def open_with_auth(self, url, method, username, password):
        return self.app.open(url,
            method=method,
            headers={
                'Authorization': 'Basic ' + base64.b64encode(username + \
                ":" + password)
            }
        )

    def test_login(self):
        ''' Check basic login flow with basic HTTP auth.
        '''
        response = self.open_with_auth('/browse', 'GET', 'Alex.Chavez@longbeach.gov', 'hunter2')
        assert response.status_code == 200

if __name__ == '__main__':
    unittest.main()
