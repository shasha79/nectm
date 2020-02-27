#
# Copyright (c) 2020 Pangeanic SL.
#
# This file is part of NEC TM
# (see https://github.com/shasha79/nectm).
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
from flask import current_app, request
from flask_principal import identity_changed, identity_loaded, Identity, RoleNeed, UserNeed, Permission, PermissionDenied
from flask_jwt import _jwt_required, current_identity, JWTError, _default_jwt_payload_handler
from flask_restful import abort
from functools import wraps

import fnmatch
import datetime

import logging

from RestApi.Models import Tags

# Admin permission requires admin role
admin_permission = Permission(RoleNeed('admin'))
# User permission requires either admin or user role
user_permission = Permission(RoleNeed('user')).union(admin_permission)

def authenticate(username, password):
  user = Users.query.get(username)
  if user and user.check_password(password):
    return user


def identity(payload):
  user = Users.query.filter(Users.username == payload['identity']).scalar()
  if user:
    # Inform Principal about loaded identity (not sure if it is needed as this happens
    # before flask-principal package is loaded)
    identity_loaded.send(current_app._get_current_object(),
                          identity=Identity(user.id))
  return user

@identity_loaded.connect
def on_identity_loaded(sender, identity):
    username = identity.id
    # Set the identity user object
    user =  Users.query.get(str(username))

    logging.info("UserScopeChecker: identity loaded for : {}, user object: {}".format(username, user))

    # Add the UserNeed to the identity
    identity.provides.add(UserNeed(user.id))

    # Assuming the User model has a role field, update the
    # identity with the role that the user provides
    identity.provides.add(RoleNeed(user.role))


# Decorator class, combining JWT token check and Principals permission check
class PermissionChecker:
  # Principal's Permission object
  def __init__(self, permission, jwt_required=_jwt_required):
    self.permission = permission
    self.jwt_required = jwt_required # function for checking JWT token

  # Wraps given func with JWT token and Principal permission check
  def __call__(self, func):
    @wraps(func)
    def wrapper(*args, **kwargs):
      # Check JWT token in the default realm (sets current_identity object)
      self.jwt_required(current_app.config['JWT_DEFAULT_REALM'])
      # Inform Principal about changed identity by sending a signal. Current identity is
      # taken from JWT-provided current_identity object
      identity_changed.send(current_app._get_current_object(),
                          identity=Identity(current_identity.id))
      ctx = self.permission.require()
      logging.info("Principal context: {}, identity: {}".format(ctx.__dict__, ctx.identity))
      # Test whether current identity has enough permissions
      try:
        self.permission.test()
      except PermissionDenied as e:
        logging.info("PermissionChecker: denied access to: {}, reason: {}".format(current_identity.id, str(e)))
        abort(403, message="You don't have sufficient permissions for this operation")
      logging.info("PermissionChecker: authorized access to: {}".format(current_identity.id))
      return func(*args, **kwargs)
    return wrapper

from RestApi.Models import Users

# Check user scope (language pair, domain, usage limit)
class UserScopeChecker:

  @staticmethod
  def check(lang_pair, domain, is_update=False, is_import=False, is_export=False):
    user = current_identity
    status = UserScopeChecker._check(user, "_".join(lang_pair), domain, is_update, is_import, is_export)
    if not status:
      logging.info(
        "UserScopeChecker: access denied to {}, language pair: {}, domain: {}, update: {}".format(user.id,
                                                                                                       lang_pair,
                                                                                                       domain,
                                                                                                       is_update))
      return False
    logging.info("UserScopeChecker: authorized access to: {}, language pair: {}, domain: {}, update: {}".format(user.id, lang_pair, domain, is_update))
    return True

  @staticmethod
  def filter_lang_pairs(lp_str_list, allow_reverse=False): # for ex. ['en_es', 'en_ar']
    user = current_identity
    if not user.scopes:
      # no scope defined, all pairs are accessible
      return lp_str_list
      #if user.role == Users.ADMIN:
      #  return lp_str_list  # no scope defined, all pairs are accessible
      #else:
      #  return []

    lp_set = set()
    for scope in user.scopes:
      if not UserScopeChecker._is_valid(scope): continue
      for lp in lp_str_list:
        if UserScopeChecker._check_pattern(scope.lang_pairs, lp):
          lp_set.add(lp)
        elif allow_reverse:
          reverse_lp = '_'.join(lp.split('_')[::-1])
          if UserScopeChecker._check_pattern(scope.lang_pairs, reverse_lp):
            lp_set.add(lp)
    return list(lp_set)


  @staticmethod
  def filter_domains(domains, lp=None, key_fn=lambda k: k, allow_unspecified=True):
    if not domains: domains = []
    user = current_identity
    if not user.scopes:
      if user.role == Users.ADMIN:
        return domains # no scope defined, all pairs are accessible
      else:
        return [d for d in domains if d["type"] == "public" or allow_unspecified and d["type"] == "unspecified" ] # return only public and unspecified tags

    domain_list = list()
    for scope in user.scopes:
      if not UserScopeChecker._is_valid(scope): continue
      if lp and not UserScopeChecker._check_pattern(scope.lang_pairs, lp): continue
      for d in domains :
        # TODO: what to do with unspecified?
        if d["type"] == "public" \
                or (allow_unspecified and d["type"] == "unspecified") \
                or UserScopeChecker._check_pattern(scope.domains, key_fn(d)):
          domain_list.append(d)
    # Remove duplicates
    return list({key_fn(v):v for v in domain_list}.values())


  @staticmethod
  def _check(user, lang_pair_str, domain_list, is_update, is_import, is_export):
    if not user.scopes or not domain_list:
      # Deny actions
      if current_identity.role != Users.ADMIN  and (is_update or is_import or is_export): return False
      return True

    today = datetime.date.today()

    found = False
    for scope in user.scopes:
      # Check for expired scope
      if scope.start_date and today < scope.start_date \
        or scope.end_date and today > scope.end_date: continue
      # Check lang pair pattern(s)
      s = UserScopeChecker._check_pattern(scope.lang_pairs, lang_pair_str)
      if not s: continue
      # Make sure all scope's domain appear in the domain_list of TU
      if domain_list:
        s = True
        for scope_domain in scope.domains.split(","):
          if scope_domain not in domain_list:
            s = False
            logging.info("Scope domain {} is not in the list: {}".format(scope_domain, domain_list))
            break
        if not s: continue
      # Check if can update (for update check only)
      if is_update and not scope.can_update or \
              is_import and not scope.can_import or \
              is_export and not scope.can_export:
        continue
      else:
        # Check usage limit (only for queiries)
        if scope.usage_limit and scope.usage_count > scope.usage_limit:
          continue
        else:
          scope.increase_usage_count(1)
      found = True
    return found

  @staticmethod
  def _is_valid(scope):
    today = datetime.date.today()
    return not(scope.start_date and today < scope.start_date \
            or scope.end_date and today > scope.end_date)

  @staticmethod
  def _check_pattern(patterns, value):
    if not value or not isinstance(value, (str,bytes)):
       logging.warning("Invalid domain value: {} - skipping".format(value))
       return False
    if not patterns: return True # any value is matching null pattern
    pattern_list = patterns.split(',')
    for p in pattern_list:
      logging.info("Checking domain(tag): {} against pattern: {}".format(value,p)) 
      if fnmatch.fnmatch(value, p):
        return True
    return False


def jwt_request_handler():
    auth_header_value = request.headers.get('Authorization', None)
    auth_header_prefix = current_app.config['JWT_AUTH_HEADER_PREFIX']

    # If no header, try extracting token from the 'token' parameter
    if not auth_header_value:
      token = request.args.get('token')
      if token: auth_header_value = '{} {}'.format(auth_header_prefix, token)

    if not auth_header_value:
      return

    parts = auth_header_value.split()

    if parts[0].lower() != auth_header_prefix.lower():
      raise JWTError('Invalid JWT header', 'Unsupported authorization type')
    elif len(parts) == 1:
      raise JWTError('Invalid JWT header', 'Token missing')
    elif len(parts) > 2:
      raise JWTError('Invalid JWT header', 'Token contains spaces')

    return parts[1]

def jwt_payload_handler(identity):
  payload = _default_jwt_payload_handler(identity)
  user = Users.query.filter(Users.username == payload['identity']).scalar()
  # If user has a normal token (with expiration date), handle as usual
  # Also, force admin user to have expiring token for security reasons
  if not user or user.token_expires or user.role == Users.ADMIN: return payload
  # Put maximal datetime as a timestamp to make non-expiring token
  payload['exp'] = datetime.datetime.max
  return payload
