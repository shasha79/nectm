#!/usr/bin/env python3
import os
import sys
import argparse
import unittest
import time
# Append to python path
script_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(script_path, "..", "src"))
sys.path.append(".")
from RestClient.RestClient import RestClient
from client import TestClient
class BasicTest(unittest.TestCase):
  TEST_CLIENT = TestClient()

  def test_manage_user(self):
    user_roles = [("test_admin", "admin"), ("test_user", "user")]
    for user,role in user_roles:
      try:
        self.TEST_CLIENT.delete_user(user)
      except:
        pass
      res = self.TEST_CLIENT.create_user(user, role)
    for user,role in user_roles:
      res = self.TEST_CLIENT.get_user(user)
      print("USER: {}".format(res))
      self.assertEqual(res["role"], role)
      self.assertEqual(res["is_active"], True)
      # assert
    for user,role in user_roles:
      self.TEST_CLIENT.delete_user(user)

  def test_stats(self):
    res = self.TEST_CLIENT.stats()

  def test_manage_tag(self):
    tag_types = [("test_private", "private"), ("test_public", "public"), ("test_unspecified", "unspecified")]
    print("TT---1---")
    for tag,type in tag_types:
      res = self.TEST_CLIENT.create_tag(tag,type)
    print("TT---2---")
    for tag,type in tag_types:
      res = self.TEST_CLIENT.get_tag(tag)
      self.assertEqual(res["type"], type)
      # assert
    # Rename
    new_name = "test_new_name"
    tag_id = tag_types[0][0]
    self.TEST_CLIENT.set_tag(tag_id, name=new_name)
    res = self.TEST_CLIENT.get_tag(tag_id)
    self.assertEqual(res["id"], tag_id)
    self.assertEqual(res["name"], new_name)

    for tag,type in tag_types:
      self.TEST_CLIENT.delete_tag(tag)

  def test_manage_tm(self):
    import time
    tag_name = "test_import"
    tag = self.TEST_CLIENT.create_tag(tag_name, "public")
    res = self.TEST_CLIENT.import_tm(os.path.join(script_path, "..", "data", "EN_SV_tmx.zip"), tag_name)
    time.sleep(3)
    res = self.TEST_CLIENT.stats()
    self.assertEqual(res["lang_pairs"]["en_sv"]["tag"][tag_name], 5)

    self._query()

    res = self.TEST_CLIENT.delete_tm("en", "sv", duplicates_only=False, filters={"tag": tag_name})
    time.sleep(3)
    res = self.TEST_CLIENT.stats()
    if "en_sv" in res["lang_pairs"]:
      self.assertEqual(res["lang_pairs"]["en_sv"]["tag"].get(tag_name, 0), 0)

  def _query(self):
    res = self.TEST_CLIENT.query(query="A license with this serial number cannot be activated.", slang="en", tlang="sv")
    self.assertGreaterEqual(len(res["results"]), 1)
    self.assertEqual(res["results"][0]["tu"]["target_text"], "Det går inte att aktivera en licens med det här serienumret.")

def parse_args():
  parser = argparse.ArgumentParser()

  parser.add_argument('--host', type=str, default="http://localhost", help="API host URL")
  parser.add_argument('--port', type=int, default=5000, help="API host port")
  parser.add_argument('--login', type=str, help="API login", default="admin")
  parser.add_argument('--pwd', type=str, help="API password", default="admin")
  parser.add_argument('tests', metavar='test', type=str, nargs='*',
                      help='tests to run')

  return parser.parse_args()


if __name__ == "__main__":
  args = parse_args()
  client = RestClient(username=args.login, password=args.pwd, host=args.host, port=args.port)
  TestClient.CLIENT = client
  sys.argv = sys.argv[0:1] + args.tests
  unittest.main()
