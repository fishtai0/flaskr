import unittest
import time

from app import create_app, db
from app.models import User, AnonymousUser, Role, Permission


class UserModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.database.create_tables(db.models, safe=True)
        Role.insert_roles()

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

    def test_valid_email_change_token(self):
        u = User(email='john@example.com', username='john', password='cat')
        u.save()
        token = u.generate_email_change_token('susan@example.org')
        self.assertTrue(u.change_email(token))
        self.assertTrue(u.email == 'susan@example.org')

    def test_invalid_email_change_token(self):
        u1 = User(email='nash@example.com', username='nash', password='cat')
        u2 = User(email='nancy@example.org', username='nancy', password='dog')
        u1.save()
        u2.save()
        token = u1.generate_email_change_token('david@example.net')
        self.assertFalse(u2.change_email(token))
        self.assertTrue(u2.email == 'nancy@example.org')

    def test_duplicate_email_change_token(self):
        u1 = User(email='joe@example.com', username='joe', password='cat')
        u2 = User(email='steve@example.org', username='steve', password='dog')
        u1.save()
        u2.save()
        token = u2.generate_email_change_token('joe@example.com')
        self.assertFalse(u2.change_email(token))
        self.assertTrue(u2.email == 'steve@example.org')

    def test_roles_and_permissions(self):
        u = User(email='paul@example.com', username='paul', password='cat')
        self.assertTrue(u.can(Permission.WRITE_ARTICLES))
        self.assertFalse(u.can(Permission.MODERATE_COMMENTS))

    def test_anonymous_user(self):
        u = AnonymousUser()
        self.assertFalse(u.can(Permission.FOLLOW))
