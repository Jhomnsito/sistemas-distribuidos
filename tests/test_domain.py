from pathlib import Path
import sys
import unittest

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from domain import OrderFields, Status, can_transition, fingerprint


class DomainTest(unittest.TestCase):
    def test_transition_matrix(self):
        for index, current in enumerate(Status):
            for target_index, target in enumerate(Status):
                with self.subTest(current=current, target=target):
                    self.assertEqual(can_transition(current, target), target_index in (index, index + 1))

    def test_normalizes_names(self):
        order = OrderFields(customer="  Cafés  ", item="  Filtro  ", quantity=1)
        self.assertEqual((order.customer, order.item), ("Cafés", "Filtro"))

    def test_rejects_malformed_input(self):
        valid = {"customer": "Cliente", "item": "Producto", "quantity": 1}
        for patch in ({"customer": " "}, {"item": "a\x00b"}, {"quantity": True},
                      {"quantity": 1000}, {"quantity": "2"}, {"status": "enviado"}):
            with self.subTest(patch=patch), self.assertRaises(ValidationError):
                OrderFields.model_validate(valid | patch)

    def test_fingerprint_binds_body_method_and_resource(self):
        data = OrderFields(customer="Cliente", item="Producto", quantity=1)
        same = OrderFields(quantity=1, item="Producto", customer=" Cliente ")
        expected = fingerprint("POST", "resource", data)
        self.assertEqual(expected, fingerprint("POST", "resource", same))
        self.assertNotEqual(expected, fingerprint("PUT", "resource", data))
        self.assertNotEqual(expected, fingerprint("POST", "other", data))
        self.assertNotEqual(expected, fingerprint("POST", "resource", data.model_copy(update={"quantity": 2})))
