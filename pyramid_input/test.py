# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: Philip J Grabner <phil@canary.md>
# date: 2015/06/13
# copy: (C) Copyright 2015-EOT Canary Health, Inc., All Rights Reserved.
#------------------------------------------------------------------------------

import unittest
from pyramid import testing
from pyramid.request import Request
from pyramid.httpexceptions import HTTPBadRequest

from pyramid_input import factory, includeme

# todo: the ordering output of `repr` should be made explicit...
#       fix that so that it is dependable!

#------------------------------------------------------------------------------
class TestInputFactory(unittest.TestCase):

  def setUp(self):
    self.config = testing.setUp()
    self.registry = self.config.registry

  def test_register(self):
    handler = factory(None, self.registry)
    self.assertEqual(handler.__name__, 'input_tween')

#------------------------------------------------------------------------------
class TestInputTween(unittest.TestCase):

  def setUp(self):
    self.config = None
    self.registry = None
    self.tween = None
    self.request = None

  def setupTween(self, handler=None, settings=None):
    # includeme(self.config)
    self.config = testing.setUp()
    self.registry = self.config.registry
    self.registry.settings = settings or {}
    self.tween = factory(handler or self.handler, self.registry)

  def setupRequest(self, url='/', data=None, ctype=None, headers=None):
    if not self.tween:
      self.setupTween()
    if ctype:
      if not headers:
        headers = dict()
      headers['content-type'] = ctype
    request = Request.blank(url, headers=headers, POST=data)
    self.request = request
    self.request.registry = self.registry

  def u2s(self, obj):
    if isinstance(obj, dict):
      return {self.u2s(k): self.u2s(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
      return [self.u2s(v) for v in obj]
    if isinstance(obj, unicode):
      try:
        return str(obj)
      except UnicodeEncodeError:
        return obj
    return obj

  def handler(self, request):
    return repr(self.u2s(request.input))

  def needYaml(self):
    try:
      import yaml
    except ImportError:
      raise unittest.SkipTest('yaml module not installed')

  #----------------------------------------------------------------------------

  def test_empty(self):
    self.setupRequest()
    self.assertEqual(self.tween(self.request), '{}')

  def test_qs_only(self):
    self.setupRequest('/path?foo=bar')
    self.assertEqual(self.tween(self.request), repr({'foo': 'bar'}))

  def test_qs_unflatten(self):
    self.setupRequest('/path?foo.zig=bar&foo.zoo-0=e0&foo.zoo-1=e1')
    self.assertEqual(self.tween(self.request), repr({'foo': {'zig': 'bar', 'zoo': ['e0', 'e1']}}))

  def test_payload_only(self):
    self.setupRequest('/path', 'foo.zig=bar&foo.zoo-0=e0&foo.zoo-1=e1')
    self.assertEqual(self.tween(self.request), repr({'foo': {'zig': 'bar', 'zoo': ['e0', 'e1']}}))

  def test_json(self):
    self.setupRequest('/path', '{"foo":{"zig":"bar","zoo":["e0","e1"]}}', ctype='application/json')
    self.assertEqual(self.tween(self.request), repr({'foo': {'zig': 'bar', 'zoo': ['e0', 'e1']}}))

  def test_json_invalid(self):
    self.setupRequest('/path', '{"foo":', ctype='application/json')
    ret = self.tween(self.request)
    self.assertEqual(ret.status_code, 400)
    self.assertEqual(str(ret), 'Invalid JSON')

  def test_yaml(self):
    self.needYaml()
    self.setupRequest('/path', 'foo:\n  zig: bar\n  zoo:\n  - e0\n  - e1', ctype='application/yaml')
    self.assertEqual(self.tween(self.request), repr({'foo': {'zig': 'bar', 'zoo': ['e0', 'e1']}}))

  def test_yaml_invalid(self):
    self.needYaml()
    self.setupRequest('/path', '{"foo":', ctype='application/yaml')
    ret = self.tween(self.request)
    self.assertEqual(ret.status_code, 400)
    self.assertEqual(str(ret), 'Invalid YAML')

  def test_xml(self):
    self.setupRequest('/path', '<foo zig="bar"><zoo>e0</zoo><zoo>e1</zoo></foo>', ctype='text/xml')
    self.assertEqual(self.tween(self.request), repr({'foo': {'zig': 'bar', 'zoo': ['e0', 'e1']}}))

  def test_xml_invalid(self):
    self.setupRequest('/path', '<foo>', ctype='application/xml')
    ret = self.tween(self.request)
    self.assertEqual(ret.status_code, 400)
    self.assertEqual(str(ret), 'Invalid XML')

  def test_xml_whitespace(self):
    self.setupRequest('/path', '''
<foo zig="bar">
  <zoo>e0</zoo>
  <zoo>e1</zoo>
  <space>  </space>
  <space idx='1'>
</space>
</foo>
''', ctype='text/xml')
    self.assertEqual(
      str(self.tween(self.request)),
      repr({'foo': {'zig': 'bar', 'zoo': ['e0', 'e1'], 'space': ['  ', {'idx': '1', None: '\n'}]}}))

  def test_bad_contentType(self):
    self.setupRequest('/path', '\x89PNG\r\n', ctype='image/png')
    ret = self.tween(self.request)
    self.assertEqual(ret.status_code, 400)
    self.assertEqual(str(ret), 'Unknown/unsupported content-type "image/png"')

  def test_combine_isolated(self):
    self.setupRequest('/path?foo=bar', 'zig=zag')
    self.assertEqual(self.tween(self.request), repr({'foo': 'bar', 'zig': 'zag'}))

  def test_combine_deep_leaves(self):
    self.setupRequest('/path?foo.a=b&foo.c=d', 'foo.c=f&foo.g=h')
    self.assertEqual(self.tween(self.request), repr({'foo': {'a': 'b', 'c': ['d', 'f'], 'g': 'h'}}))

  def test_combine_deep_branch(self):
    self.setupRequest('/path?foo.a=b&foo.c=d', 'foo=h')
    self.assertEqual(self.tween(self.request), repr({'foo': [{'a': 'b', 'c': 'd'}, 'h']}))

  def test_combine_conflict_merge(self):
    self.setupRequest('/path?foo=bar', 'foo=zag')
    self.assertEqual(self.tween(self.request), repr({'foo': ['bar', 'zag']}))

  def test_combine_conflict_override(self):
    self.setupTween(settings={'pyramid_input.combine.deep': False})
    self.setupRequest('/path?foo=bar', 'foo=zag')
    self.assertEqual(self.tween(self.request), repr({'foo': 'zag'}))

  def test_config_native_dict(self):
    def handler_aadict(request):
      return repr(self.u2s(request.input.zig.zag.zog))
    def handler_dict(request):
      return repr(self.u2s(request.input['zig']['zag']['zog']))
    self.setupTween(handler=handler_dict)
    self.setupRequest('/path?zig.zag.zog=bar')
    self.assertEqual(self.tween(self.request), repr('bar'))
    self.setupTween(handler=handler_aadict)
    self.setupRequest('/path?zig.zag.zog=bar')
    self.assertEqual(self.tween(self.request), repr('bar'))
    self.setupTween(handler=handler_dict, settings={'pyramid_input.native-dict': True})
    self.setupRequest('/path?zig.zag.zog=bar')
    self.assertEqual(self.tween(self.request), repr('bar'))
    self.setupTween(handler=handler_aadict, settings={'pyramid_input.native-dict': True})
    self.setupRequest('/path?zig.zag.zog=bar')
    with self.assertRaises(AttributeError) as cm:
      self.tween(self.request)
    self.assertEqual(str(cm.exception), "'dict' object has no attribute 'zig'")

  def test_config_attribute_name(self):
    def handler_data(request):
      return repr(self.u2s(request.data))
    self.setupTween(handler=handler_data)
    self.setupRequest('/path?foo=bar')
    with self.assertRaises(AttributeError) as cm:
      self.tween(self.request)
    self.assertEqual(str(cm.exception), "'Request' object has no attribute 'data'")
    self.setupTween(handler=handler_data, settings={'pyramid_input.attribute-name': 'data'})
    self.setupRequest('/path?foo=bar')
    self.assertEqual(self.tween(self.request), repr({'foo': 'bar'}))

  def test_config_enabled(self):
    self.setupRequest('/path?foo=bar')
    self.assertEqual(self.tween(self.request), repr({'foo': 'bar'}))
    self.setupTween(settings={'pyramid_input.enabled': False})
    self.setupRequest('/path?foo=bar')
    with self.assertRaises(AttributeError) as cm:
      self.tween(self.request)
    self.assertEqual(str(cm.exception), "'Request' object has no attribute 'input'")

  def test_config_exclude(self):
    def handler(request):
      return repr(self.u2s(getattr(request, 'input', None)))
    self.setupTween(handler=handler, settings={'pyramid_input.exclude': '/a /b/**'})
    self.setupRequest('/path?foo=bar')
    self.assertEqual(self.tween(self.request), repr({'foo': 'bar'}))
    self.setupRequest('/a?foo=bar')
    self.assertEqual(self.tween(self.request), repr(None))
    self.setupRequest('/a/path?foo=bar')
    self.assertEqual(self.tween(self.request), repr({'foo': 'bar'}))
    self.setupRequest('/b?foo=bar')
    self.assertEqual(self.tween(self.request), repr({'foo': 'bar'}))
    self.setupRequest('/b/path/zoo?foo=bar')
    self.assertEqual(self.tween(self.request), repr(None))

  def test_config_include(self):
    def handler(request):
      return repr(self.u2s(getattr(request, 'input', None)))
    self.setupTween(handler=handler, settings={'pyramid_input.include': '/a /a/**'})
    self.setupRequest('/path?foo=bar')
    self.assertEqual(self.tween(self.request), repr(None))
    self.setupRequest('/a?foo=bar')
    self.assertEqual(self.tween(self.request), repr({'foo': 'bar'}))
    self.setupRequest('/a/path?foo=bar')
    self.assertEqual(self.tween(self.request), repr({'foo': 'bar'}))

  def test_config_require_dict(self):
    self.setupRequest('/path', 'foo: bar', ctype='application/yaml')
    self.assertEqual(self.tween(self.request), repr({'foo': 'bar'}))
    self.setupRequest('/path', '["foo", "bar"]', ctype='application/yaml')
    ret = self.tween(self.request)
    self.assertEqual(ret.status_code, 400)
    self.assertEqual(str(ret), 'Payload must evaluate to dict-type')
    self.setupTween(settings={'pyramid_input.require-dict': False})
    self.setupRequest('/path', 'foo: bar', ctype='application/yaml')
    self.assertEqual(self.tween(self.request), repr({'foo': 'bar'}))
    self.setupRequest('/path', '["foo", "bar"]', ctype='application/yaml')
    self.assertEqual(self.tween(self.request), repr(['foo', 'bar']))

  def test_config_fail_unknown(self):
    self.setupRequest('/path', '\x89PNG\r\n', ctype='image/png')
    ret = self.tween(self.request)
    self.assertEqual(ret.status_code, 400)
    self.assertEqual(str(ret), 'Unknown/unsupported content-type "image/png"')
    self.setupTween(settings={'pyramid_input.fail-unknown': False})
    self.setupRequest('/path', '\x89PNG\r\n', ctype='image/png')
    self.assertEqual(self.tween(self.request), repr({}))

  def test_config_error_handler(self):
    def error_handler(request, error):
      import json
      request.response.status_code = error.code
      request.response.content_type = 'application/json'
      request.response.body = json.dumps({
        'status'  : error.code,
        'message' : str(error)
      })
      return request.response
    self.setupTween(settings={'pyramid_input.error-handler': error_handler})
    self.setupRequest('/path', '<|>-+-<|>', ctype='application/xml')
    ret = self.tween(self.request)
    self.assertEqual(ret.status_code, 400)
    self.assertEqual(ret.content_type, 'application/json')
    self.assertEqual(ret.body, '{"status": 400, "message": "Invalid XML"}')

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
