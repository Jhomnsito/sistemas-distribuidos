"""Comprobaciones de credenciales y sesión sobre un laboratorio aislado."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import auth_store


class AuthStoreTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        db = patch.object(auth_store, "DATABASE", os.path.join(folder.name, "auth.sqlite"))
        db.start()
        self.addCleanup(db.stop)
        auth_store.setup()

    def test_policy_and_password_rotation(self):
        with self.assertRaises(ValueError):
            auth_store.validate_password("abcdefghijkl!", "admin")
        with self.assertRaises(ValueError):
            auth_store.validate_password("123456789012!", "cliente")
        password = "a!0123456789"
        auth_store.provision("esteban_cliente", password)
        auth_store.provision("esteban_admin", password)
        with auth_store.store() as db:
            rows = db.execute("SELECT salt, digest FROM accounts").fetchall()
        self.assertNotEqual(rows[0]["salt"], rows[1]["salt"])
        self.assertNotEqual(rows[0]["digest"], rows[1]["digest"])
        credential = auth_store.credentials("esteban_cliente", password)
        cookie = auth_store.new_session("esteban_cliente", credential, 30, "")
        self.assertEqual(auth_store.lookup(cookie), {"subject": "demo-alba", "role": "cliente"})
        auth_store.provision("esteban_cliente", "a!012345678X")
        self.assertIsNone(auth_store.lookup(cookie))
        self.assertIsNone(auth_store.new_session("esteban_cliente", credential, 30, ""))

    def test_expiration_and_revocation(self):
        password = "a!0123456789"
        auth_store.provision("esteban_admin", password)
        credential = auth_store.credentials("esteban_admin", password)
        with patch.object(auth_store, "time", return_value=100):
            cookie = auth_store.new_session("esteban_admin", credential, 5, "")
            self.assertEqual(auth_store.lookup(cookie)["role"], "admin")
            revoked = auth_store.new_session("esteban_admin", credential, 60, "")
            auth_store.revoke(revoked)
            self.assertIsNone(auth_store.lookup(revoked))
        with patch.object(auth_store, "time", return_value=105):
            self.assertIsNone(auth_store.lookup(cookie))

    def test_shared_throttle(self):
        with patch.object(auth_store, "time", return_value=100):
            for expected in (0, 0, 5):
                self.assertEqual(auth_store.take_attempt("esteban_admin"), 0)
                self.assertEqual(auth_store.failed_attempt("esteban_admin"), expected)
            self.assertEqual(auth_store.take_attempt("esteban_admin"), 5)
        with patch.object(auth_store, "time", return_value=104.9):
            self.assertEqual(auth_store.take_attempt("esteban_admin"), 1)
        with patch.object(auth_store, "time", return_value=105):
            self.assertEqual(auth_store.take_attempt("esteban_admin"), 0)
            self.assertEqual(auth_store.failed_attempt("esteban_admin"), 0)

    def test_first_run_preserves_existing_password(self):
        self.assertEqual(auth_store.initial_missing(), ["esteban_cliente", "esteban_admin"])
        password = "a!0123456789"
        self.assertTrue(auth_store.provision("esteban_cliente", password, only_new=True))
        self.assertFalse(auth_store.provision("esteban_cliente", "b!0123456789", only_new=True))
        self.assertEqual(auth_store.initial_missing(), ["esteban_admin"])
        self.assertIsNotNone(auth_store.credentials("esteban_cliente", password))

    def test_failures_do_not_disconnect_active_session(self):
        password = "a!0123456789"
        auth_store.provision("esteban_cliente", password)
        cookie = auth_store.new_session("esteban_cliente", auth_store.credentials("esteban_cliente", password), 60, "")
        for _ in range(3):
            auth_store.failed_attempt("esteban_cliente")
        self.assertEqual(auth_store.lookup(cookie)["role"], "cliente")
        self.assertGreater(auth_store.take_attempt("esteban_cliente"), 0)
        for _ in range(3):
            auth_store.failed_attempt("inexistente")
        self.assertGreater(auth_store.take_attempt("inexistente"), 0)

    def test_account_block_and_audit(self):
        password = "a!0123456789"
        auth_store.provision("esteban_cliente", password)
        auth_store.provision("esteban_admin", password)
        cookie = auth_store.new_session("esteban_cliente", auth_store.credentials("esteban_cliente", password), 60, "")
        with self.assertRaises(ValueError):
            auth_store.set_client_block("esteban_admin", True, "admin")
        auth_store.set_client_block("esteban_cliente", True, "admin")
        self.assertIsNone(auth_store.lookup(cookie))
        self.assertIsNone(auth_store.credentials("esteban_cliente", password))
        auth_store.set_client_block("esteban_cliente", False, "admin")
        self.assertIsNotNone(auth_store.credentials("esteban_cliente", password))
        self.assertIsNone(auth_store.lookup(cookie))
        activity = auth_store.activity()
        self.assertEqual(activity["clients"][0]["disabled"], 0)
        self.assertIn("cuenta_bloqueada", {row["action"] for row in activity["events"]})
        self.assertNotIn(password, str(activity))
        self.assertNotIn(cookie, str(activity))
