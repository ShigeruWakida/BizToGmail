import unittest

from fastapi.testclient import TestClient

from biztogmail_web.app import app


class WebUiTests(unittest.TestCase):
    def test_root_serves_html_console(self):
        client = TestClient(app)
        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("BizToGmail Console", response.text)
        self.assertIn('id="authStatus"', response.text)
        self.assertIn('id="loginBtn"', response.text)
        self.assertIn('id="logoutBtn"', response.text)
        self.assertIn('id="sourceProtocol"', response.text)
        self.assertIn('id="sourceFolder"', response.text)
        self.assertIn('id="smtpHost"', response.text)
        self.assertIn('id="smtpPort"', response.text)
        self.assertIn('id="smtpUsername"', response.text)
        self.assertIn('id="smtpPassword"', response.text)
        self.assertIn('id="smtpUseSsl"', response.text)
        self.assertIn('data-action="edit"', response.text)
        self.assertIn('data-action="delete"', response.text)
        self.assertNotIn('id="destinationEmail"', response.text)
        self.assertNotIn('/gmail/labels', response.text)
