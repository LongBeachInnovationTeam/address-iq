import unittest
import mock
import os
import datetime
import pytz
from httmock import response, HTTMock

os.environ['APP_SETTINGS'] = 'config.TestingConfig'

from app import app, db
from app import fetch_incidents_at_address, count_incidents_by_timeframes
from app import get_top_incident_reasons_by_timeframes
import models

from count_calls_for_service import count_calls

from factories import FireIncidentFactory, StandardizedFireIncidentFactory, PoliceIncidentFactory, StandardizedPoliceIncidentFactory, BusinessLicenseFactory, UserFactory

from flask.ext.login import login_user

def get_date_days_ago(days):
    return datetime.datetime.now() - datetime.timedelta(days=days)

def persona_verify(url, request):
    if url.geturl() == 'https://verifier.login.persona.org/verify':
        return response(200, '''{"status": "okay", "email": "user@example.com"}''')

    else:
        raise Exception('Asked for unknown URL ' + url.geturl())

def setup_google_mock(can_view='Y', can_view_fire='Y', email='user@example.com'):
    mock_client = mock.MagicMock()
    instance = mock_client.return_value

    worksheets_mock = mock.Mock()
    worksheet_mock = mock.Mock()
    worksheet_mock.id = mock.Mock()
    worksheet_mock.id.text = 'foo/bar/abc'
    worksheets_mock.entry = [worksheet_mock]
    instance.get_worksheets.return_value = worksheets_mock

    sample_row = {
        'email': email,
        'name': 'Joe Fireworks',
        'canviewsite': can_view,
        'canviewfiredata': can_view_fire
    }
    row_mock = mock.Mock()
    row_mock.to_dict.return_value = sample_row
    list_feed_mock = mock.Mock()
    list_feed_mock.entry = [row_mock]
    instance.get_list_feed.return_value = list_feed_mock

    return mock_client

class HomeTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()

    def testHomePageReturns200(self):
        rv = self.app.get('/')

        assert rv.status_code == 200

class LoginTestCase(unittest.TestCase):
    # @maybe: Refactor test_login and test_logout.

    # @todo: Integrate this with others, probably, so you confirm that access
    # control is as it should be throughout.

    def setUp(self):
        self.app = app.test_client()
        db.create_all()

    def tearDown(self):
        db.drop_all()

    @mock.patch('app.SpreadsheetsClient', setup_google_mock())
    def test_login(self):
        ''' Check basic log in flow without talking to Persona.
        '''
        response = self.app.get('/')
        self.assertFalse('user@example.com' in response.data)

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})
            self.assertEquals(response.status_code, 200)

        response = self.app.get('/browse')
        self.assertTrue('user@example.com' in response.data)

    @mock.patch('app.SpreadsheetsClient', setup_google_mock(email="notexample@example.com"))
    def test_login_fails_when_not_in_spreadsheet(self):
        response = self.app.get('/')
        self.assertFalse('user@example.com' in response.data)

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})

        self.assertEquals(response.status_code, 403)

        response = self.app.get('/')
        self.assertFalse('user@example.com' in response.data)

    @mock.patch('app.SpreadsheetsClient', setup_google_mock(can_view='N'))
    def test_login_fails_when_not_allowed_to_view(self):
        response = self.app.get('/')
        self.assertFalse('user@example.com' in response.data)

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})

        self.assertEquals(response.status_code, 403)

        response = self.app.get('/')
        self.assertFalse('user@example.com' in response.data)

    @mock.patch('app.SpreadsheetsClient', setup_google_mock())
    def test_login_successfully_pulls_in_name(self):
        response = self.app.get('/')
        self.assertFalse('user@example.com' in response.data)

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})
            self.assertEquals(response.status_code, 200)

        response = self.app.get('/browse')
        self.assertTrue('Joe Fireworks' in response.data)

    @mock.patch('app.SpreadsheetsClient', setup_google_mock(can_view_fire='Y'))
    def test_login_successfully_pulls_in_fire_viewable_true(self):
        response = self.app.get('/')
        self.assertFalse('user@example.com' in response.data)

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})
            self.assertEquals(response.status_code, 200)

        user = db.session.query(models.User).filter(models.User.email=='user@example.com').first()
        assert user.can_view_fire_data == True

    @mock.patch('app.SpreadsheetsClient', setup_google_mock(can_view_fire='N'))
    def test_login_successfully_pulls_in_fire_viewable_false(self):
        response = self.app.get('/')
        self.assertFalse('user@example.com' in response.data)

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})
            self.assertEquals(response.status_code, 200)

        user = db.session.query(models.User).filter(models.User.email=='user@example.com').first()
        assert user.can_view_fire_data == False

    @mock.patch('app.SpreadsheetsClient', setup_google_mock())
    def test_logout(self):
        ''' Check basic log out flow without talking to Persona.
        '''
        response = self.app.get('/')

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})

        response = self.app.get('/')

        response = self.app.post('/log-out')
        self.assertEquals(response.status_code, 200)

        response = self.app.get('/')
        self.assertFalse('user@example.com' in response.data)


class AddressUtilityTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        db.create_all()

    def tearDown(self):
        db.drop_all()

    def test_fetch_incidents_at_address_returns_all_empty_types(self):

        incidents = fetch_incidents_at_address("123 main st")

        assert 'fire' in incidents
        assert 'police' in incidents
        assert 'businesses' in incidents

        assert len(incidents['fire']) == 0
        assert len(incidents['police']) == 0
        assert len(incidents['businesses']) == 0

    def test_fetch_incident_at_address_returns_correct_number_of_items(self):
        [StandardizedFireIncidentFactory(standardized_address="123 MAIN ST")
         for i in range(5)]
        [StandardizedPoliceIncidentFactory(standardized_address="123 MAIN ST")
         for i in range(3)]
        [BusinessLicenseFactory(business_address="123 MAIN ST")
         for i in range(1)]

        db.session.flush()

        incidents = fetch_incidents_at_address("123 MAIN ST")
        assert len(incidents['fire']) == 5
        assert len(incidents['police']) == 3
        assert len(incidents['businesses']) == 1

    def test_fetch_incident_at_address_works_if_lowercase_supplied(self):
        [StandardizedFireIncidentFactory(standardized_address="123 MAIN ST")
         for i in range(0, 5)]
        [StandardizedPoliceIncidentFactory(standardized_address="123 MAIN ST")
         for i in range(0, 3)]
        [BusinessLicenseFactory(business_address="123 MAIN ST")
         for i in range(0, 1)]

        db.session.flush()

        incidents = fetch_incidents_at_address("123 main st")
        assert len(incidents['fire']) == 5
        assert len(incidents['police']) == 3
        assert len(incidents['businesses']) == 1

    def test_count_incidents_returns_proper_counts_for_default_days(self):
        [StandardizedFireIncidentFactory(standardized_address="123 MAIN ST",
                             alarm_datetime=get_date_days_ago(5))
         for i in range(0, 5)]
        [StandardizedFireIncidentFactory(standardized_address="123 MAIN ST",
                             alarm_datetime=get_date_days_ago(20))
         for i in range(0, 8)]
        [StandardizedFireIncidentFactory(standardized_address="123 MAIN ST",
                             alarm_datetime=get_date_days_ago(40))
         for i in range(0, 7)]
        [StandardizedFireIncidentFactory(standardized_address="123 MAIN ST",
                             alarm_datetime=get_date_days_ago(200))
         for i in range(0, 10)]

        [StandardizedPoliceIncidentFactory(standardized_address="123 MAIN ST",
                               call_datetime=get_date_days_ago(5))
         for i in range(0, 3)]
        [StandardizedPoliceIncidentFactory(standardized_address="123 MAIN ST",
                               call_datetime=get_date_days_ago(20))
         for i in range(0, 8)]
        [StandardizedPoliceIncidentFactory(standardized_address="123 MAIN ST",
                               call_datetime=get_date_days_ago(40))
         for i in range(0, 9)]
        [StandardizedPoliceIncidentFactory(standardized_address="123 MAIN ST",
                               call_datetime=get_date_days_ago(200))
         for i in range(0, 6)]

        db.session.flush()

        incidents = fetch_incidents_at_address("123 main st")
        counts = count_incidents_by_timeframes(incidents, [7, 30, 90, 365])

        assert counts['fire'][7] == 5
        assert counts['fire'][30] == 13
        assert counts['fire'][90] == 20
        assert counts['fire'][365] == 30

        assert counts['police'][7] == 3
        assert counts['police'][30] == 11
        assert counts['police'][90] == 20
        assert counts['police'][365] == 26

    def test_count_incidents_returns_zeros_when_no_incidents(self):
        incidents = fetch_incidents_at_address("123 main st")
        counts = count_incidents_by_timeframes(incidents, [7, 30, 90, 365])

        assert counts['fire'][7] == 0
        assert counts['fire'][30] == 0
        assert counts['fire'][90] == 0
        assert counts['fire'][365] == 0

        assert counts['police'][7] == 0
        assert counts['police'][30] == 0
        assert counts['police'][90] == 0
        assert counts['police'][365] == 0

    def test_top_incident_reasons_by_timeframes_returns_proper_counts(self):
        [StandardizedFireIncidentFactory(standardized_address="123 MAIN ST",
                             alarm_datetime=get_date_days_ago(5),
                             actual_nfirs_incident_type_description="Broken Nose")
         for i in range(0, 5)]
        [StandardizedFireIncidentFactory(standardized_address="123 MAIN ST",
                             alarm_datetime=get_date_days_ago(20),
                             actual_nfirs_incident_type_description="Stubbed Toe")
         for i in range(0, 8)]
        [StandardizedFireIncidentFactory(standardized_address="123 MAIN ST",
                             alarm_datetime=get_date_days_ago(40),
                             actual_nfirs_incident_type_description="Myocardial Infarction")
         for i in range(0, 7)]
        [StandardizedFireIncidentFactory(standardized_address="123 MAIN ST",
                             alarm_datetime=get_date_days_ago(200),
                             actual_nfirs_incident_type_description="Lung Fell Off")
         for i in range(0, 10)]

        [StandardizedPoliceIncidentFactory(standardized_address="123 MAIN ST",
                               call_datetime=get_date_days_ago(5),
                               final_cad_call_type_description="Stepped on a Crack")
         for i in range(0, 3)]
        [StandardizedPoliceIncidentFactory(standardized_address="123 MAIN ST",
                               call_datetime=get_date_days_ago(20),
                               final_cad_call_type_description="Whipped It")
         for i in range(0, 8)]
        [StandardizedPoliceIncidentFactory(standardized_address="123 MAIN ST",
                               call_datetime=get_date_days_ago(40),
                               final_cad_call_type_description="Safety Dance")
         for i in range(0, 9)]
        [StandardizedPoliceIncidentFactory(standardized_address="123 MAIN ST",
                               call_datetime=get_date_days_ago(200),
                               final_cad_call_type_description="Runnin' With The Devil")
         for i in range(0, 6)]


        db.session.flush()


        incidents = fetch_incidents_at_address("123 MAIN ST")
        actual_top_reasons = get_top_incident_reasons_by_timeframes(incidents, [7, 30, 90, 365])

        expected_top_reasons = {
           'fire': {
               7: [('Broken Nose', 5)],
               30: [('Stubbed Toe', 8), ('Broken Nose', 5)],
               90: [('Stubbed Toe', 8), ('Myocardial Infarction', 7), ('Broken Nose', 5)],
               365: [('Lung Fell Off', 10), ('Stubbed Toe', 8), ('Myocardial Infarction', 7), ('Broken Nose', 5)]
           },
           'police': {
               7: [('Stepped on a Crack', 3)],
               30: [('Whipped It', 8), ('Stepped on a Crack', 3)],
               90: [('Safety Dance', 9), ('Whipped It', 8), ('Stepped on a Crack', 3)],
               365: [('Safety Dance', 9), ('Whipped It', 8), ("Runnin' With The Devil", 6), ('Stepped on a Crack', 3)]
           }
        }

        self.assertEquals(expected_top_reasons, actual_top_reasons)

    def test_top_incident_reasons_by_timeframes_returns_empty_lists_if_no_incident(self):
        incidents = fetch_incidents_at_address("123 MAIN ST")
        actual_top_reasons = get_top_incident_reasons_by_timeframes(incidents, [7, 30, 90, 365])

        expected_top_reasons = {
           'fire': {
               7: [],
               30: [],
               90: [],
               365: []
           },
           'police': {
               7: [],
               30: [],
               90: [],
               365: []
           }
        }

        self.assertEquals(expected_top_reasons, actual_top_reasons)

    def test_address_page_with_incidents_returns_200(self):
        [StandardizedFireIncidentFactory(standardized_address="123 MAIN ST")
         for i in range(0, 5)]

        db.session.flush()

        rv = self.app.get('/address/123 main st')
        assert rv.status_code == 200

    def test_address_page_with_no_incidents_returns_404(self):
        rv = self.app.get('/address/123 main st')
        assert "Page not found" in rv.data

    def test_address_page_shows_correct_address(self):
        [StandardizedFireIncidentFactory(standardized_address="456 LALA LN")
         for i in range(0, 5)]
        db.session.flush()

        rv = self.app.get('/address/456 lala ln')
        assert '456 Lala Ln' in rv.data

    def test_address_page_shows_correct_business_info_with_no_businesses(self):
        [StandardizedFireIncidentFactory(standardized_address="456 LALA LN")
         for i in range(0, 5)]
        db.session.flush()

        rv = self.app.get('/address/456 lala ln')
        assert 'No business is registered' in rv.data

    def test_address_page_shows_correct_business_info_with_one_business(self):
        [StandardizedFireIncidentFactory(standardized_address="456 LALA LN")
         for i in range(0, 5)]

        [BusinessLicenseFactory(business_address="456 LALA LN",
                                business_service_description="Bar",
                                name="The Pub")]
        db.session.flush()

        rv = self.app.get('/address/456 lala ln')
        assert "Bar" in rv.data
        assert "The Pub" in rv.data

    def test_address_page_shows_correct_business_info_with_multiple_businesses(self):
        [StandardizedFireIncidentFactory(standardized_address="456 LALA LN")
         for i in range(0, 5)]

        BusinessLicenseFactory(business_address="456 LALA LN",
                               business_service_description="Bar",
                               name="The Pub")
        BusinessLicenseFactory(business_address="456 LALA LN",
                               business_service_description="Lawncare",
                               name="Mowers R Us")
        db.session.flush()

        rv = self.app.get('/address/456 lala ln')
        assert "Bar, Lawncare" in rv.data
        assert "The Pub, Mowers R Us" in rv.data

    def test_no_comment_msg_shows_on_address_with_none(self):
        [StandardizedFireIncidentFactory(standardized_address="456 LALA LN")
         for i in range(0, 5)]

        db.session.flush()

        rv = self.app.get('/address/456 lala ln')
        assert 'no-action-found' in rv.data
        assert 'Nothing has been done yet with this address. Add a note below, or click the activate button!' in rv.data

    @mock.patch('app.SpreadsheetsClient', setup_google_mock())
    def test_posting_a_comment_loads_a_comment_into_database(self):
        [StandardizedFireIncidentFactory(standardized_address="456 LALA LN")
         for i in range(0, 5)]

        db.session.flush()

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})

        rv = self.app.post('/address/456 lala ln/comments', data={
                'content': 'This is a test comment'
            })
        self.assertEquals(302, rv.status_code)

        comments = models.Action.query.all()
        self.assertEquals(1, len(comments))

    @mock.patch('app.SpreadsheetsClient', setup_google_mock())
    def test_posting_a_comment_shows_it_on_the_page(self):
        [StandardizedFireIncidentFactory(standardized_address="456 LALA LN")
         for i in range(0, 5)]

        db.session.flush()

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})

        rv = self.app.post('/address/456 lala ln/comments', data={
                'content': 'This is a test comment'
            })
        self.assertEquals(302, rv.status_code)

        rv = self.app.get('/address/456 lala ln')
        assert 'This is a test comment' in rv.data

    @mock.patch('app.SpreadsheetsClient', setup_google_mock())
    def test_posting_two_comments_shows_the_most_recent_last(self):
        [StandardizedFireIncidentFactory(standardized_address="456 LALA LN")
         for i in range(0, 5)]

        db.session.flush()

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})

        self.app.post('/address/456 lala ln/comments', data={
                'content': 'Test 1'
        })
        self.app.post('/address/456 lala ln/comments', data={
                'content': 'Test 2'
        })

        rv = self.app.get('/address/456 lala ln')
        assert 'Test 1' in rv.data
        assert 'Test 2' in rv.data
        assert rv.data.find('Test 1') < rv.data.find('Test 2')

    @mock.patch('app.SpreadsheetsClient', setup_google_mock())
    def test_logging_in_creates_an_audit_log(self):
        app.config['AUDIT_DISABLED'] = False

        db.session.flush()

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})

        del app.config['AUDIT_DISABLED']

        # Length should be 2: one log entry for login, one for accessing page.
        assert len(models.AuditLogEntry.query.all()) == 1

        first_entry = models.AuditLogEntry.query.first()
        assert first_entry.user_id != None
        assert first_entry.resource == '/log-in'
        assert first_entry.method == 'POST'
        assert first_entry.response_code == "200"

    @mock.patch('app.SpreadsheetsClient', setup_google_mock())
    def test_viewing_an_address_creates_an_audit_log(self):
        app.config['AUDIT_DISABLED'] = False

        [StandardizedFireIncidentFactory(standardized_address="456 LALA LN")
         for i in range(0, 5)]

        db.session.flush()

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})

        rv = self.app.get('/address/456 lala ln')

        del app.config['AUDIT_DISABLED']

        # Length should be 2: one log entry for login, one for accessing page.
        assert len(models.AuditLogEntry.query.all()) == 2

        second_entry = models.AuditLogEntry.query.all()[1]
        assert second_entry.user_id != None
        assert second_entry.method == 'GET'
        assert second_entry.resource == '/address/456 lala ln'
        assert second_entry.response_code == "200"

    @mock.patch('app.SpreadsheetsClient', setup_google_mock())
    def test_posting_a_comment_creates_an_audit_log(self):
        app.config['AUDIT_DISABLED'] = False

        [StandardizedFireIncidentFactory(standardized_address="456 LALA LN")
         for i in range(0, 5)]

        db.session.flush()

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})

        rv = self.app.post('/address/456 lala ln/comments', data={
            'content': 'This is a test comment'
        })

        del app.config['AUDIT_DISABLED']

        # Length should be 2: one log entry for login, one for accessing page.
        assert len(models.AuditLogEntry.query.all()) == 2

        second_entry = models.AuditLogEntry.query.all()[1]
        assert second_entry.user_id != None
        assert second_entry.method == 'POST'
        assert second_entry.resource == '/address/456 lala ln/comments'
        assert second_entry.response_code == "302"

    @mock.patch('app.SpreadsheetsClient', setup_google_mock(can_view_fire='N'))
    def test_viewing_an_address_does_not_show_fire_data_if_not_allowed(self):
        [StandardizedFireIncidentFactory(standardized_address="456 LALA LN", alarm_datetime=get_date_days_ago(5),
                             actual_nfirs_incident_type_description="Broken Nose")
         for i in range(0, 5)]

        db.session.flush()

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})

        rv = self.app.get('/address/456 lala ln')
        assert 'Broken Nose' not in rv.data

    @mock.patch('app.SpreadsheetsClient', setup_google_mock())
    def test_activation_endpoint_activates_address(self):
        [StandardizedFireIncidentFactory(standardized_address="456 LALA LN")
         for i in range(0, 5)]

        db.session.flush()

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})

        rv = self.app.post('/address/456 lala ln/activate')

        assert 200 == rv.status_code
        assert 1 == len(models.ActivatedAddress.query.all())

    @mock.patch('app.SpreadsheetsClient', setup_google_mock())
    def test_deactivation_endpoint_deactivates_address(self):
        [StandardizedFireIncidentFactory(standardized_address="456 LALA LN")
         for i in range(0, 5)]

        db.session.flush()

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})

        self.app.post('/address/456 lala ln/activate')
        rv = self.app.post('/address/456 lala ln/deactivate')

        assert 200 == rv.status_code
        assert 0 == len(models.ActivatedAddress.query.all())

    @mock.patch('app.SpreadsheetsClient', setup_google_mock())
    def test_activating_address_adds_to_action_station(self):
        [StandardizedFireIncidentFactory(standardized_address="456 LALA LN")
         for i in range(0, 5)]

        db.session.flush()

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})

        self.app.post('/address/456 lala ln/activate')
        rv = self.app.get('/address/456 lala ln')

        assert 200 == rv.status_code
        assert 'activated this address' in rv.data

    @mock.patch('app.SpreadsheetsClient', setup_google_mock())
    def test_deactivating_address_adds_to_action_station(self):
        [StandardizedFireIncidentFactory(standardized_address="456 LALA LN")
         for i in range(0, 5)]

        db.session.flush()

        with HTTMock(persona_verify):
            response = self.app.post('/log-in', data={'assertion': 'sampletoken'})

        self.app.post('/address/456 lala ln/activate')
        self.app.post('/address/456 lala ln/deactivate')
        rv = self.app.get('/address/456 lala ln')

        assert 200 == rv.status_code
        assert 'deactivated this address' in rv.data


class CountCallsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        db.create_all()

    def tearDown(self):
        db.drop_all()

    def test_count_calls_returns_empty_when_given_no_incidents(self):
        counts = count_calls([], 'alarm_datetime', 'fire_counts', [7, 14])

        assert counts == {}

    def test_count_calls_returns_correctly_for_fire_responses(self):
        def get_date_days_ago(days):
            return datetime.datetime.now(pytz.utc) - datetime.timedelta(days=days)

        incidents = [StandardizedFireIncidentFactory(standardized_address="123 MAIN ST",
                             alarm_datetime=get_date_days_ago(5))
         for i in range(0, 5)]

        incident_tuples = [(incident.standardized_address, incident.alarm_datetime)
                            for incident in incidents]

        counts = count_calls(incident_tuples, 'alarm_datetime', 'fire_counts', [7, 14])

        assert '123 MAIN ST' in counts
        assert 'fire_counts' in counts['123 MAIN ST']
        assert 7 in counts['123 MAIN ST']['fire_counts']
        assert counts['123 MAIN ST']['fire_counts'][7] == 5
        assert counts['123 MAIN ST']['fire_counts'][14] == 5

    def test_count_calls_returns_correctly_for_police_responses(self):
        def get_date_days_ago(days):
            return datetime.datetime.now(pytz.utc) - datetime.timedelta(days=days)

        incidents = [StandardizedPoliceIncidentFactory(standardized_address="123 MAIN ST",
                             call_datetime=get_date_days_ago(5))
         for i in range(0, 5)]

        incident_tuples = [(incident.standardized_address, incident.call_datetime)
                            for incident in incidents]
        counts = count_calls(incident_tuples, 'call_datetime', 'police_counts', [7, 14])

        assert '123 MAIN ST' in counts
        assert 'police_counts' in counts['123 MAIN ST']
        assert 7 in counts['123 MAIN ST']['police_counts']
        assert counts['123 MAIN ST']['police_counts'][7] == 5
        assert counts['123 MAIN ST']['police_counts'][14] == 5

if __name__ == '__main__':
    unittest.main()
