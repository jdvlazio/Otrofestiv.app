"""pipeline/ig_posts.py: la memoria del vigía se lee sin Apify, colaborativos incluidos."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'pipeline'))
import ig_posts as p  # noqa: E402


class DeLaCuenta(unittest.TestCase):
    def test_propio_y_colaborativo(self):
        self.assertTrue(p.de_la_cuenta({'ownerUsername': 'a'}, 'a'))
        self.assertTrue(p.de_la_cuenta({'ownerUsername': 'b', 'coauthorProducers': [{'username': 'a'}]}, 'a'))
        self.assertFalse(p.de_la_cuenta({'ownerUsername': 'b'}, 'a'))


if __name__ == '__main__':
    unittest.main()
