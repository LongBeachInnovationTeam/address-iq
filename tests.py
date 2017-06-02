import unittest
import mock
import os
import datetime
import pytz
from httmock import response, HTTMock

os.environ['APP_SETTINGS'] = 'config.TestingConfig'

from extensions import app, db
from app import fetch_incidents_at_address, count_incidents_by_timeframes
from app import get_top_incident_reasons_by_timeframes
import models

from count_calls_for_service import count_calls

from factories import FireIncidentFactory, StandardizedFireIncidentFactory, PoliceIncidentFactory, StandardizedPoliceIncidentFactory, BusinessLicenseFactory, UserFactory

from flask.ext.login import login_user
import base64

def get_date_days_ago(days):
    return datetime.datetime.now() - datetime.timedelta(days=days)

class HomeTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()

    def tearDown(self):
        pass

    def testHomePageReturns200(self):
        response = self.app.get('/')
        assert response.status_code == 200

class LoginTestCase(unittest.TestCase):


    def setUp(self):
        self.app = app.test_client()
        # user_datastore = SQLAlchemyUserDatastore(db, models.User, models.Role)
        # self.security = Security(self.app, user_datastore)
        db.create_all()

        # Create an admin user
        # user_admin_role = models.Role(name='admin', description='Administrator')
        user_admin = models.User(name = 'Test User', \
            email = 'test@email.com', \
            password = 'hunter2', \
            date_created = datetime.datetime.now(pytz.utc), \
            can_view_fire_data = False, \
            active = True)
        user_admin.roles.append(models.Role(name='admin', description='Administrator'))
        db.session.add(user_admin)
        db.session.commit()

        # Create an approved-user user
        user_approved = models.User(name='Test User', \
            email='test2@email.com', \
            password='hunter3', \
            date_created=datetime.datetime.now(pytz.utc), \
            can_view_fire_data = False, \
            active = False)
        user_approved.roles.append(models.Role(name='approved-user', description='Accounts approved to access app.'))
        db.session.add(user_approved)
        db.session.commit()

        # Create a yet-to-be-approved user
        new_user = models.User(name='Test User', \
            email='test3@email.com', \
            password='hunter4', \
            date_created=datetime.datetime.now(pytz.utc), \
            can_view_fire_data = False, \
            active = False)
        db.session.add(new_user)
        db.session.commit()

    def tearDown(self):
        db.drop_all()

    def open_with_auth(self, url, method, username, password):
        auth_string = 'Basic ' + base64.b64encode(username + ':' + password)
        return self.app.open(url,
            method = method,
            headers = {
                'Authorization': auth_string
            }
        )

    def test_login(self):
        ''' Check basic login flow with basic HTTP auth.
        '''
        response = self.open_with_auth('/browse', 'GET', 'test@email.com', 'hunter2')
        assert response.status_code == 200

    def test_login_passes_with_approved_user(self):
        ''' Check basic login flow with basic HTTP auth
            for an approved user who is not an admin.
        '''
        response = self.open_with_auth('/browse', 'GET', 'test2@email.com', 'hunter3')
        assert response.status_code == 200

    def test_login_fails_when_not_admin_or_approved_user(self):
        response = self.open_with_auth('/browse', 'GET', 'test3@email.com', 'hunter4')
        assert response.status_code != 200

if __name__ == '__main__':
    unittest.main()
