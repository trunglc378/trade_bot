"""Check funding rounding so neither fees nor exchange steps underfund the reserve."""
import importlib.util
from pathlib import Path
import unittest
import tempfile
from decimal import Decimal as D

spec = importlib.util.spec_from_file_location('reserve_funding', Path(__file__).resolve().parents[1] / 'freqtrade-bot/reserve_funding.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ReserveFundingTests(unittest.TestCase):
    def test_minimal_quantity_after_fees_on_both_venues(self):
        for price, step in [('81971', '.00001'), ('81970.4', '.00000001')]:
            with self.subTest(price=price):
                q = module.quantity_for_target(100, price, '.001', step)
                self.assertGreaterEqual(q*D(price)*D('.999'), D(100))
                self.assertLess((q-D(step))*D(price)*D('.999'), D(100))

    def test_rejects_wider_authorization_or_bad_fee(self):
        for values in [(101, 80000, '.001', '.00001'), (100, 0, '.001', '.00001'),
                       (100, 80000, '.1', '.00001'), (100, 80000, '.001', 0)]:
            with self.assertRaises(ValueError):
                module.quantity_for_target(*values)

    def test_protects_unlocked_bot_coin_and_recognizes_verified_stop_lock(self):
        self.assertEqual(module.usable_free('.00123', '.00013', 0, 0), D('.00110'))
        self.assertEqual(module.usable_free('.00123', '.00013', '.00013', '.00013'), D('.00123'))
        # An unrelated locked order must not release the bot's free coin.
        self.assertEqual(module.usable_free('.00123', '.00013', 0, '.00013'), D('.00110'))

    def test_second_execution_cannot_claim_the_same_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'receipt.json'
            module.claim_receipt(path, {'stage': 'prepared'})
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                module.claim_receipt(path, {'stage': 'duplicate'})
            self.assertEqual(path.read_bytes(), before)
