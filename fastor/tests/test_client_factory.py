import unittest

from fastor.client import getClient
from fastor.client.client import FastorClient, VanillaClient


class FactoryTestCase(unittest.TestCase):

    def test_factory(self):
        fastor_client = getClient("fastor")
        self.assertIsInstance(fastor_client, FastorClient)

        vanilla_client = getClient("vanilla")
        self.assertIsInstance(vanilla_client, VanillaClient)
