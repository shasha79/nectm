#!/usr/bin/env python3
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

# Tags itself:
#   Public tags: the tags are shown to all users
#   Unspecified: the tags are shown to all users
#   Private: the tags are shown to users with these tags in their scopes

# Content tagged:
#   Public content:
#     Query: the content can be queried by all users
#     Import: the content can be imported only by admin, unless special permission is given
#     Export: the content can be exported only by admin, unless special permission is given
#     Update: the content can be updated only by admin, unless special permission is given

#   Unspecified content (only tag):
#     Query: the content can be queried only by admin
#     Import: the content can be imported by all users <- recommended *1
#     Export: the content can be exported only by admin <- recommended *1
#     Update:  the content can be updated by all users <- recommended *1

#   Private content (only private tag):
#     Query: the content can be queried only by admin, unless special permission is given  *2
#     Import: the content can be imported only by admin, unless special permission is given  *2
#     Export: the content can be exported only by admin, unless special permission is given  *2
#     Update: the content can be updated only by admin, unless special permission is given  *2

#   Private(s) + Unspecified(s) content:
#     Query: the content can be queried only by admin, unless special permission is given for *2
#     Import: the content can be imported only by admin, unless special permission is given *2
#     Export: the content can be exported only by admin, unless special permission is given *2
#     Update: the content can be updated only by admin, unless special permission is given *2

#   Public(s) + Unspecified(s) content:
#     Query: the content can be queried by all users
#     Import: the content can be imported only by admin, unless special permission is given
#     Export: the content can be exported only by admin, unless special permission is given
#     Update: the content can be updated only by admin, unless special permission is given

#   Public(s) + Private(s) content:
#     Query: the content can be queried by all users, but the "private tag" will not be shown unless special permission is given in the scopes *3
#     Import: the content can be imported only by admin, unless special permission is given
#     Export: the content can be exported only by admin, unless special permission is given
#     Update: the content can be Update only by admin, unless special permission is given

#   Public(s) + Private(s) + Unspecified(s) content:
#     Query: the content can be queried by all users, but the "private tag" will not be shown  unless special permission is given in the scopes
#     Import: the content can be imported only by admin, unless special permission is given
#     Export: the content can be exported only by admin, unless special permission is given
#     Update: the content can be updated only by admin, unless special permission is given

# *1: It will be ideal if we can't select only unspecified tags, that is mandatory also select a private and/or public tag(s).
# *2: If the permission in the scope is given to the "private" tag, the permission is given to the full "private tag", including the user will be able to access the content with "private tag" + "unspecified tag"
# *3: I'm referring to here:
class PermissionBaseTest(unittest.TestCase):
  TEST_CLIENT = TestClient()

  def _client(self):
    return self.TEST_CLIENT.CLIENT

  def _get_test_type(self):
    return self.id().split('.')[-1].split('_')[-1]

  def _init_test_user(self):
    username = "test_user"
    res = self.TEST_CLIENT.create_user(username, "user")
    self.user_client = RestClient(username=username, password=username)
    self.user_client.base_url = self.TEST_CLIENT.CLIENT.base_url

  def _create_test_tags(self, type):
    tags = []
    for ttype in type.split('1'):
      tag = "tag_{}".format(ttype)
      self.TEST_CLIENT.create_tag(tag, ttype)
      tags.append(tag)
    return tags

  def _delete_all_tags(self):
    for ttype in ['private', 'public', 'unspecified']:
      try:
        self.TEST_CLIENT.delete_tag("tag_{}".format(ttype))
      except:
        # Tag may not exist, ignore
        pass

  def _import_test_data(self, tags):
    res = self._client().import_tm(os.path.join(script_path, "..", "data", "EN_SV_tmx.zip"), tags)

  def _delete_test_data(self):
    res = self._client().delete_tm("en", "sv", duplicates_only=False)
    self._client().delete_user("test_user")
    time.sleep(3)

  def setUp(self):
    print("=================== START TEST {} ====================".format(self.id()))
    self._setUp()

  def tearDown(self):
    self._tearDown()
    print("=================== END TEST {} ====================".format(self.id()))

  def _setUp(self):
    raise ("Pemission test class should implement set up")

  def _tearDown(self):
    raise ("Pemission test class should implement tear down")


class PermissionQueryTest(PermissionBaseTest):

  def _setUp(self):
    #self.skipTest('TMP')

    self._init_test_user()
    self._delete_all_tags()
    tags = self._create_test_tags(self._get_test_type())
    self._import_test_data(tags)

  def _tearDown(self):
    self._delete_test_data()

  # Public content:
  # 	Query: the content can be queried by all users
  def test_query_public(self):
    self._query(expected_results=1)

  # Unspecified content (only tag):
  # 	Query: the content can be queried only by admin
  def test_query_unspecified(self):
    self._query(expected_results=0)
    self.TEST_CLIENT.add_scope("test_user", "tag_unspecified")
    self._query(expected_results=1)

  # Private content (only private tag):
  # 	Query: the content can be queried only by admin, unless special permission is given *2
  def test_query_private(self):
    self._query(expected_results=0)
    self.TEST_CLIENT.add_scope("test_user", "tag_private")
    self._query(expected_results=1)

  #   Private(s) + Unspecified(s) content:
  #     Query: the content can be queried only by admin, unless special permission is given for *2
  def test_query_private1unspecified(self):
    self._query(expected_results=0)
    self.TEST_CLIENT.add_scope("test_user", "tag_unspecified")
    self._query(expected_results=1, expected_tags=["tag_unspecified"])
    self.TEST_CLIENT.add_scope("test_user", "tag_private,tag_unspecified")
    self._query(expected_results=1, expected_tags=["tag_private","tag_unspecified"])

  #   Public(s) + Unspecified(s) content:
  #     Query: the content can be queried by all users
  def test_query_public1unspecified(self):
    self._query(expected_results=1)

  #   Public(s) + Private(s) content:
  #     Query: the content can be queried by all users, but the "private tag" will not be shown unless special permission is given in the scopes *3
  def test_query_public1private(self):
    self._query(expected_results=1, expected_tags=["tag_public"])

  #   Public(s) + Private(s) + Unspecified(s) content:
  #     Query: the content can be queried by all users, but the "private tag" will not be shown unless special permission is given in the scopes
  def test_query_public1private1unspecified(self):
    self._query(expected_results=1, expected_tags=["tag_public"])
    # TODO: should tag_unspecified appear too?

  def _query(self, expected_results=1, expected_tags=None):
    res = self.user_client.query(query="A license with this serial number cannot be activated.", slang="en", tlang="sv")
    #print("Query results: {}".format(res))
    self.assertEqual(len(res["results"]), expected_results)
    if expected_results > 0:
      self.assertEqual(res["results"][0]["tu"]["target_text"], "Det går inte att aktivera en licens med det här serienumret.")
      if expected_tags:
        self.assertEqual(set(res["results"][0]["tag"]),
                         set(expected_tags))


class PermissionImportTest(PermissionBaseTest):

  def _setUp(self):
    self._init_test_user()
    self._delete_all_tags()
    self.tags = self._create_test_tags(self._get_test_type())

  def _tearDown(self):
    self._delete_test_data()

  # Public content:
  #     Import: the content can be imported only by admin, unless special permission is given
  def test_import_public(self):
    self._import(self.tags, expected_result=False)
    self.TEST_CLIENT.add_scope("test_user", "tag_public", can_import=True)
    self._import(self.tags, expected_result=True)

  #   Unspecified content (only tag):
  #     Import: the content can be imported by all users <- recommended *1
  def test_import_unspecified(self):
    self._import(self.tags, expected_result=False)
    self.TEST_CLIENT.add_scope("test_user", "tag_unspecified", can_import=True)
    self._import(self.tags, expected_result=False)

  #   Private content (only private tag):
  #     Import: the content can be imported only by admin, unless special permission is given *2
  def test_import_private(self):
    print("******* Importing data (1) **********************")
    self._import(self.tags, expected_result=False)
    self.TEST_CLIENT.add_scope("test_user", "tag_private", can_import=True)
    print("******* Importing data (2) **********************")
    self._import(self.tags, expected_result=True)

  def test_import_public1private(self):
    self._import(self.tags, expected_result=False)
    self.TEST_CLIENT.add_scope("test_user", "tag_public,tag_private", can_import=True)
    # Separately, tags should fail
    self._import(["tag_public"], expected_result=False)
    self._import(["tag_private"], expected_result=False)
    self._import(self.tags, expected_result=True)

  def test_import_public1unspecified(self):
    self._test_specified_and_unspecified(['tag_public'])

  def test_import_private1unspecified(self):
    self._test_specified_and_unspecified(['tag_private'])

  def test_import_public1private1unspecified(self):
    self._test_specified_and_unspecified(['tag_public', 'tag_private'])

  def _import(self, tags, expected_result):
    try:
      res = self.user_client.import_tm(os.path.join(script_path, "..", "data", "EN_SV_tmx.zip"), tags)
      print("RES: --> ",res)
      self.assertTrue(expected_result)
    except requests.exceptions.HTTPError as e:
      self.assertFalse(expected_result)
      self.assertEqual(e.response.status_code, 403)

  def _test_specified_and_unspecified(self, specified_tags):
    # No permission for specified + unspecified tags -> fail
    self._import(self.tags, expected_result=False)
    # Add permissions for specified tags only -> should be good enough (e.g. no need permission for unspecified)
    self.TEST_CLIENT.add_scope("test_user", "{}".format(','.join(specified_tags)), can_import=True)
    self._import(self.tags, expected_result=True)
    # Add permissions for specified and unspecified tags
    self.TEST_CLIENT.add_scope("test_user", "{},tag_unspecified".format(','.join(specified_tags)), can_import=True)
    # Only unspecified tags - should fail
    self._import(["tag_unspecified"], expected_result=False)
    self._import(self.tags, expected_result=True)


class PermissionExportTest(PermissionBaseTest):

  def _setUp(self):
    self._init_test_user()
    self._delete_all_tags()
    self.tags = self._create_test_tags(self._get_test_type())
    self._import_test_data(self.tags)

  def _tearDown(self):
    self._delete_test_data()


  def test_export_public(self):
    self._export(self.tags, expected_result=False)
    self.TEST_CLIENT.add_scope("test_user", "tag_public", can_export=True)
    self._export(self.tags, expected_result=True)

  def test_export_unspecified(self):
    self._export(self.tags, expected_result=False)
    self.TEST_CLIENT.add_scope("test_user", "tag_unspecified", can_export=True)
    self._export(self.tags, expected_result=False)

  def test_export_private(self):
    self._export(self.tags, expected_result=False)
    self.TEST_CLIENT.add_scope("test_user", "tag_private", can_export=True)
    self._export(self.tags, expected_result=True)

  def test_export_public1private(self):
    self._export(self.tags, expected_result=False)
    self.TEST_CLIENT.add_scope("test_user", "tag_public,tag_private", can_export=True)
    # Separately, tags should fail
    self._export(["tag_public"], expected_result=False)
    self._export(["tag_private"], expected_result=False)
    self._export(self.tags, expected_result=True)

  def test_export_public1unspecified(self):
    #self._test_specified_and_unspecified(['tag_public'])
    pass

  def test_export_private1unspecified(self):
    #self._test_specified_and_unspecified(['tag_private'])
    pass

  def test_export_public1private1unspecified(self):
    # self._test_specified_and_unspecified(['tag_public', 'tag_private'])
    pass


  def _export(self, tags, expected_result):
    try:
      res = self.user_client.export_tm("en", "sv", filters={"tag": tags})
      print("RES: --> ",res)
      self.assertTrue(expected_result)
    except requests.exceptions.HTTPError as e:
      self.assertFalse(expected_result)
      self.assertEqual(e.response.status_code, 403)


# En licens med detta serienummer kan inte aktiveras.
class PermissionUpdateTest(PermissionBaseTest):

  def _setUp(self):
    self._init_test_user()
    self._delete_all_tags()
    self.tags = self._create_test_tags(self._get_test_type())
    #self._import_test_data(self.tags)

  def _tearDown(self):
    self._delete_test_data()

  def test_update_public(self):
    self._update(self.tags, expected_result=False)
    self.TEST_CLIENT.add_scope("test_user", "tag_public", can_update=True)
    self._update(self.tags, expected_result=True)

  def test_update_unspecified(self):
    self._update(self.tags, expected_result=False)
    self.TEST_CLIENT.add_scope("test_user", "tag_unspecified", can_update=True)
    self._update(self.tags, expected_result=False)

  def test_update_private(self):
    print("******* Importing data (1) **********************")
    self._update(self.tags, expected_result=False)
    self.TEST_CLIENT.add_scope("test_user", "tag_private", can_update=True)
    print("******* Importing data (2) **********************")
    self._update(self.tags, expected_result=True)

  def test_update_public1private(self):
    self._update(self.tags, expected_result=False)
    self.TEST_CLIENT.add_scope("test_user", "tag_public,tag_private", can_update=True)
    # Separately, tags should fail
    self._update(["tag_public"], expected_result=False)
    self._update(["tag_private"], expected_result=False)
    self._update(self.tags, expected_result=True)

  def test_update_public1unspecified(self):
    self._test_specified_and_unspecified(['tag_public'])

  def test_update_private1unspecified(self):
    self._test_specified_and_unspecified(['tag_private'])

  def test_update_public1private1unspecified(self):
    self._test_specified_and_unspecified(['tag_public', 'tag_private'])

  def _update(self, tags, expected_result, expected_tags=None):
    stext = "A license with this serial number cannot be activated."
    ttext = "En licens med detta serienummer kan inte aktiveras."
    if not expected_tags: expected_tags = tags
    try:
      res = self.user_client.add_tu(stext, ttext, "en", "sv", tags)
      print("RES: --> ",res)
      self.assertTrue(expected_result)
      time.sleep(2) # Let the ES to update
      self._assert_query(stext, ttext, expected_results=1, expected_tags=expected_tags)
    except requests.exceptions.HTTPError as e:
      self.assertFalse(expected_result)
      self.assertEqual(e.response.status_code, 403)

  def _assert_query(self, stext, ttext, expected_results=1, expected_tags=None):
    res = self.user_client.query(query=stext, slang="en", tlang="sv")
    #print("Query results: {}".format(res))
    self.assertEqual(len(res["results"]), expected_results)
    if expected_results > 0:
      self.assertEqual(res["results"][0]["tu"]["target_text"], ttext)
      if expected_tags:
        self.assertEqual(set(res["results"][0]["tag"]),
                         set(expected_tags))


  def _test_specified_and_unspecified(self, specified_tags):
    # No permission for specified + unspecified tags -> fail
    self._update(self.tags, expected_result=False)
    # Add permissions for specified tags only -> should be good enough (e.g. no need permission for unspecified)
    self.TEST_CLIENT.add_scope("test_user", "{}".format(','.join(specified_tags)), can_update=True)
    self._update(self.tags, expected_result=True, expected_tags=specified_tags)
    # Add permissions for specified and unspecified tags
    self.TEST_CLIENT.add_scope("test_user", "{},tag_unspecified".format(','.join(specified_tags)), can_update=True)
    # Only unspecified tags - should fail
    self._update(["tag_unspecified"], expected_result=False)
    self._update(self.tags, expected_result=True)



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
