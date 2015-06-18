# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: Philip J Grabner <phil@canary.md>
# date: 2015/06/13
# copy: (C) Copyright 2015-EOT Canary Health, Inc., All Rights Reserved.
#------------------------------------------------------------------------------

from pyramid.settings import aslist, asbool
from pyramid.httpexceptions import HTTPException, HTTPBadRequest
import logging
import asset
from aadict import aadict
import globre
import formencode
import morph
try:
  import yaml
except ImportError:
  yaml = None

from .i18n import _

#------------------------------------------------------------------------------

log = logging.getLogger(__name__)

CONFIG_PREFIX               = 'pyramid_input.'
DEFAULT_ATTRIBUTE_NAME      = 'input'

FORM_CTYPES_PREFIX          = 'application/x-www-form-urlencoded', 'multipart/form-data',
JSON_CTYPES_PREFIX          = 'application/json', 'application/x-json', 'text/json', 'text/x-json'
JSON_CTYPES_SUFFIX          = '+json',
YAML_CTYPES_PREFIX          = 'application/yaml', 'application/x-yaml', 'text/yaml', 'text/x-yaml'
YAML_CTYPES_SUFFIX          = '+yaml',
XML_CTYPES_PREFIX           = 'application/xml',  'application/x-xml',  'text/xml',  'text/x-xml'
XML_CTYPES_SUFFIX           = '+xml',

ERRMSG_UNSUPPORTED          = 'Unknown/unsupported content-type "{content_type}"'
ERRMSG_DICTTYPE             = 'Payload must evaluate to dict-type'
ERRMSG_INVJSON              = 'Invalid JSON'
ERRMSG_INVYAML              = 'Invalid YAML'
ERRMSG_INVXML               = 'Invalid XML'

#------------------------------------------------------------------------------
def factory(handler, registry):
  get          = morph.pick(registry.settings, prefix=CONFIG_PREFIX).get
  conf         = aadict()
  conf.enabled = asbool(get('enabled', True))
  conf.include = [globre.compile(el, globre.EXACT)
                  for el in aslist(get('include', []))]
  conf.exclude = [globre.compile(el, globre.EXACT)
                  for el in aslist(get('exclude', []))]
  conf.name    = get('attribute-name', DEFAULT_ATTRIBUTE_NAME)
  conf.deep    = asbool(get('combine.deep', True))
  conf.reqdict = asbool(get('require-dict', True))
  conf.failunk = asbool(get('fail-unknown', True))
  conf.ndict   = asbool(get('native-dict', False))
  conf.error   = get('error-handler', None)
  if conf.error:
    conf.error = asset.symbol(conf.error)
  conf.xfmt    = asbool(get('xml.enable', True))
  conf.jfmt    = asbool(get('json.enable', True))
  conf.yfmt    = asbool(get('yaml.enable', bool(yaml or get('yaml.parser'))))
  if conf.jfmt:
    conf.jparser = get('json.parser', None)
    if conf.jparser:
      conf.jparser = asset.symbol(conf.jparser)
  if conf.yfmt:
    conf.yparser = asset.symbol(get('yaml.parser', 'yaml.load'))
  if conf.xfmt:
    conf.xparser = asset.symbol(get('xml.parser', 'xml.etree.ElementTree.fromstring'))
  def input_tween(request):
    return process(handler, request, conf)
  return input_tween

#------------------------------------------------------------------------------
def process(handler, request, conf):
  try:
    decorate(request, conf)
  except HTTPException as exc:
    if conf.error:
      return conf.error(request, exc)
    return exc
  return handler(request)

#------------------------------------------------------------------------------
def decorate(request, conf):
  if not conf.enabled:
    return
  if conf.include:
    for el in conf.include:
      if el.match(request.path):
        break
    else:
      return
  if conf.exclude:
    for el in conf.exclude:
      if el.match(request.path):
        return
  setattr(request, conf.name, compute(request, conf))

#------------------------------------------------------------------------------
def isContentType(request, prefixes=None, suffixes=None):
  ctype = request.content_type.split(';', 1)[0].split(',', 1)[0]
  for ct in prefixes or []:
    if ctype.startswith(ct):
      return True
  for ct in suffixes or []:
    if ctype.endswith(ct):
      return True
  return False

#------------------------------------------------------------------------------
def mergeInto(base, items, deep=True):
  for k, v in items:
    if k in base:
      if deep and isinstance(v, dict) and isinstance(base[k], dict):
        base[k] = mergeInto(base[k], v.items(), True)
      else:
        if not isinstance(base[k], list):
          base[k] = [base[k]]
        base[k].append(v)
    else:
      base[k] = v
  return base

#------------------------------------------------------------------------------
def compute(request, conf):
  if conf.ndict:
    return _compute(request, conf)
  return aadict.d2ar(_compute(request, conf))

#------------------------------------------------------------------------------
def _compute(request, conf):
  qs = parse_pairs(request.GET, conf)
  pay = None
  if request.content_type and request.content_length:
    if isContentType(request, FORM_CTYPES_PREFIX):
      pay = parse_pairs(request.POST, conf)
    elif conf.jfmt and isContentType(request, JSON_CTYPES_PREFIX, JSON_CTYPES_SUFFIX):
      pay = parse_json(request, conf)
    elif conf.yfmt and isContentType(request, YAML_CTYPES_PREFIX, YAML_CTYPES_SUFFIX):
      pay = parse_yaml(request, conf)
    elif conf.xfmt and isContentType(request, XML_CTYPES_PREFIX, XML_CTYPES_SUFFIX):
      pay = parse_xml(request, conf)
    else:
      if conf.failunk:
        raise HTTPBadRequest(_(ERRMSG_UNSUPPORTED).format(
          content_type=request.content_type))
  if pay:

    # import pdb;pdb.set_trace()


    if conf.reqdict and not morph.isdict(pay):
      raise HTTPBadRequest(ERRMSG_DICTTYPE)
    if not qs or not morph.isdict(pay):
      return pay
    if conf.deep:
      qs = mergeInto(qs, pay.items(), True)
    else:
      qs.update(pay)
  return qs

#------------------------------------------------------------------------------
def parse_pairs(pairs, conf):
  ret = mergeInto(dict(), pairs.items(), False)
  try:
    return dict(formencode.variabledecode.variable_decode(ret))
  except Exception:
    # todo: raise an exception?...
    return ret

#------------------------------------------------------------------------------
def parse_json(request, conf):
  try:
    if conf.jparser:
      return conf.jparser(request.body)
    return request.json_body
  except ValueError:
    log.exception('failed parsing JSON')
    raise HTTPBadRequest(_(ERRMSG_INVJSON))

#------------------------------------------------------------------------------
def parse_yaml(request, conf):
  try:
    return conf.yparser(request.body)
  except Exception:
    log.exception('failed parsing YAML')
    raise HTTPBadRequest(_(ERRMSG_INVYAML))

#------------------------------------------------------------------------------
def node2pair(node):
  ret = dict(node.items())
  if node.text:
    if len(ret) <= 0 and len(node) <= 0:
      return (node.tag, node.text)
    if len(node) <= 0 or node.text.strip():
      ret[None] = node.text
  mergeInto(ret, [node2pair(n) for n in node])
  return (node.tag, ret)

#------------------------------------------------------------------------------
def parse_xml(request, conf):
  try:
    doc = conf.xparser(request.body)
  except Exception:
    log.exception('failed parsing XML')
    raise HTTPBadRequest(_(ERRMSG_INVXML))
  return dict([node2pair(doc)])

#------------------------------------------------------------------------------
def includeme(config):
  '''
  Adds a pyramid :term:`tween` to `config` that parses and combines
  all request data sources into a single data tree. See
  `https://github.com/canaryhealth/pyramid_input`_ for details.
  '''
  if asbool(config.registry.settings.get(CONFIG_PREFIX + 'enabled', True)):
    config.add_tween('pyramid_input.factory')

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
