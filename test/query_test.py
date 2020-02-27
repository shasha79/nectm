import os
import sys
import argparse
import unittest
import time
import requests
# Append to python path
script_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(script_path, "..", "src"))
from RestClient.RestClient import RestClient
from client import TestClient

class QueryTest(unittest.TestCase):
  TEST_CLIENT = TestClient()

  def _client(self):
    return self.TEST_CLIENT.CLIENT

  def setUp(self):
    tag1 = self.TEST_CLIENT.create_tag("tag_public1", "public")

    #res = self._client().import_tm(os.path.join(script_path, "..", "data", "EN_SV_tmx.zip"), "tag_public1")
    res = self.TEST_CLIENT.create_user("test_user", "user")
    self.user_client = RestClient(username="test_user", password="test_user")
    self.user_client.base_url = self.TEST_CLIENT.CLIENT.base_url

  def tearDown(self):
    try:
      self.TEST_CLIENT.delete_tag("tag_public1")
      self.TEST_CLIENT.delete_tag("tag_public2")
    except:
      # Tag may not exist, ignore
      pass
    #res = self._client().delete_tm("en", "sv", duplicates_only=False)
    self._client().delete_user("test_user")
    time.sleep(3)

  def test_query(self):
    texts = [ ("This is my purple car","Detta är min lila bil"),
              ("This is my red car", "Det här är min röda bil"),
              ("This is my yellow car", "Det här är min gula bil"),
          ]
    tag1 = self.TEST_CLIENT.create_tag("tag_public1", "public")
    tag2 = self.TEST_CLIENT.create_tag("tag_public2", "public")
    res = self.TEST_CLIENT.CLIENT.add_tu(texts[0][0], texts[0][1], "en", "sv", "tag_public1")
    res = self.TEST_CLIENT.CLIENT.add_tu(texts[1][0], texts[1][1], "en", "sv", "tag_public2")
    time.sleep(2) # Let the ES to update
    # Simplet same-tag queries
    self._assert_query(texts[0][0], texts[0][1], expected_results=1)
    self._assert_query(texts[1][0], texts[1][1], expected_results=1)
    # Cross-tag queries (with concordance)
    self._assert_query(texts[0][0], texts[1][1], expected_results=1, tags="tag_public2", concordance=True)
    self._assert_query(texts[1][0], texts[0][1], expected_results=1, tags="tag_public1", concordance=True)

    # Concordance search with slightly different query, matching both records
    self._assert_query(texts[2][0], None, expected_results=2, concordance=True)
    self._assert_query(texts[2][0], None, expected_results=1, concordance=True, tags='tag_public1')


  def _assert_query(self, stext, ttext, tags=None, concordance=False, expected_results=1, expected_tags=None):
    res = self.TEST_CLIENT.query(query=stext, slang="en", tlang="sv", tag=tags, concordance=concordance)
    #print("Query results: {}".format(res))
    self.assertEqual(len(res["results"]), expected_results)
    if expected_results > 0:
      if ttext:
        self.assertEqual(res["results"][0]["tu"]["target_text"], ttext)
      if expected_tags:
        self.assertEqual(set(res["results"][0]["tag"]),
                         set(expected_tags))



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
