from RestClient.RestClient import RestClient

class TestClient:
  CLIENT=RestClient()

  def create_user(self, user, role):
    res = self.CLIENT.set_user(username=user, role=role, password=user) #
    return res

  def create_tag(self, tag, type):
    res = self.CLIENT.set_tag(tag, type=type, name=tag)
    return res

  def delete_tag(self, tag):
    res = self.CLIENT.delete_tag(tag)
    return res


  def add_scope(self, user, tag, can_import=None, can_export=None, can_update=None):
    res = self.CLIENT.set_user_scope(user, tags=tag, can_import=can_import, can_export=can_export, can_update=can_update)
    return res

  def delete_scope(self, user, scope):
    res = self.CLIENT.delete_scope(user, scope)
    return res

  def import_tm(self, tmx_file, tags):
    res = self.CLIENT.import_tm(tmx_file=tmx_file, domain=tags)
    return res

  def delete_tm(self, slang, tlang, **kwargs):
    return self.CLIENT.delete_tm(slang, tlang, **kwargs)

  def stats(self):
    return self.CLIENT.stats()

  def query(self, query, slang, tlang, **kwargs):
    return self.CLIENT.query(query, slang, tlang, **kwargs)

  def get_user(self, user):
    return self.CLIENT.get_user(user)

  def delete_user(self, user):
    return self.CLIENT.delete_user(user)

  def get_tag(self, tag):
    return self.CLIENT.get_tag(tag)

  def set_tag(self, tag, name):
    return self.CLIENT.set_tag(tag, name=name)