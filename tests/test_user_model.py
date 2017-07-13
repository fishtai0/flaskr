import unittest
import time

from app import create_app, db
from app.models import User


class UserModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.database.create_tables(db.models, safe=True)

    def tearDown(self):
        db.database.drop_tables(db.models, safe=True)
        self.app_context.pop()

    def test_password_setter(self):
        u = User(password='cat')
        self.assertTrue(u.password_hash is not None)

    def test_no_password_getter(self):
        u = User(password='cat')
        with self.assertRaises(AttributeError):
            u.password

    def test_password_verification(self):
        u = User(password='cat')
        self.assertTrue(u.verify_password('cat'))
        self.assertFalse(u.verify_password('dog'))

    def test_password_salts_are_random(self):
        u = User(password='cat')
        u2 = User(password='cat')
        self.assertTrue(u.password_hash != u2.password_hash)

    def test_valid_confirmation_token(self):
        u = User(email='u@example.com', username='u', password='cat')
        u.save()
        token = u.generate_confirmation_token()
        self.assertTrue(u.confirm(token))

    def test_invalid_confirmation_token(self):
        u1 = User(email='u1@example.com', username='u1', password='cat')
        u2 = User(email='u2@example.com', username='u2', password='dog')
        u1.save()
        u2.save()
        token = u1.generate_confirmation_token()
        self.assertFalse(u2.confirm(token))

    def test_expired_confirmation_token(self):
        u3 = User(email='u3@example.com', username='u3', password='cat')
        u3.save()
        token = u3.generate_confirmation_token(1)
        time.sleep(2)
        self.assertFalse(u3.confirm(token))

    def test_valid_reset_token(self):
        u4 = User(email='u4@example.com', username='u4', password='cat')
        u4.save()
        token = u4.generate_reset_token()
        self.assertTrue(u4.reset_password(token, 'dog'))
        self.assertTrue(u4.verify_password('dog'))

    def test_invalid_reset_token(self):
        u5 = User(email='u5@example.com', username='u5', password='cat')
        u6 = User(email='u6@example.com', username='u6', password='dog')
        u5.save()
        u6.save()
        token = u5.generate_reset_token()
        self.assertFalse(u6.reset_password(token, 'horse'))
        self.assertTrue(u6.verify_password('dog'))
