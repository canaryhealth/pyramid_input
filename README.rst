=============
Pyramid Input
=============

The ``pyramid_input`` package is a pyramid plugin that adds a "tween"
that parses and combines all data presented in the HTTP request in one
standardized request attribute. The following data is currently accepted
(in increasing order of precedence):

* Query string parameters
* Request payload (i.e. the "request body") in several different formats

See `Example`_ for a detailed example.


Project
=======

* Homepage: https://github.com/canaryhealth/pyramid_input
* Bugs: https://github.com/canaryhealth/pyramid_input/issues


Installation
============

.. code:: bash

  $ pip install pyramid_input


Usage
=====

Enable the tween either in your INI file via:

.. code:: ini

  pyramid.includes = pyramid_input

or in code in your package's application initialization via:

.. code:: python

  def main(global_config, **settings):
    # ...
    config.include('pyramid_input')
    # ...

If needed, adjust pyramid_input's behaviour by setting the various
`Configuration`_ options in your INI file.

Then, access a request's input parameters, regardless of their
origin or encoding, simply as:

.. code:: python

  def request_handler(request):

    if request.input.somekey == 'some-value':
      ...


Example
=======

The pyramid_input tween makes all of the following requests present
the identical structure in the `request.input` attribute:

Interpreting GET data:

.. code:: text

  GET /path?foo=bar&zig.zag=zog&zig.zen-0=mig&zig.zen-1=mag

Interpreting and merging GET and POST form data:

.. code:: text

  POST /path?foo=bar
  Content-Type: application/x-www-form-urlencoded

  zig.zag=zog&zig.zen-0=mig&zig.zen-1=mag

Interpreting and merging GET and JSON payload data:

.. code:: text

  POST /path?foo=bar
  Content-Type: application/json

  {"zig": {"zag": "zog", "zen": ["mig", "mag"]}}

Interpreting and merging GET and YAML payload data:

.. code:: text

  POST /path?foo=bar
  Content-Type: application/yaml

  zig:
    zag: zog
    zen:
      - mig
      - mag

Interpreting and merging GET and XML payload data:

.. code:: text

  POST /path?foo=bar
  Content-Type: application/xml

  <zig>
    <zag>zog</zag>
    <zen>mig</zen>
    <zen>mag</zen>
  </zig>

All of the above will result in the identical data structure being
contained in the `request.input` attribute:

.. code:: python

  request.input = {
    'foo': 'bar',
    'zig': {
      'zag': 'zog',
      'zen': ['mig', 'mag']
    }
  }

Please note that in all cases the original parameters (in
`request.GET`, `request.POST`, `request.params`, `request.body` and
`request.json_body`) are left as-is, so if the raw data is needed, it
can be accessed directly.


Query String Parsing
====================

The HTTP query string parameters are "unflattened" using FormEncode's
`variable_decode` implementation, which converts the key-value pairs
into a nested tree structure. For example, the following query string
parameters:

.. code:: text

  ?simple=val1&dict.subkey=val2&dict.list-0=el0&dict.list-1=el1

is transformed into the structure:

.. code:: yaml

   {
     simple: val1
     dict: {
       subkey: val2
       list: [ el0, el1 ]
     }
   }

Note that query string parameters are by default overwritten by any
HTTP request payload data.


Payload Parsing
===============

The request payload (aka. request body) is parsed when the request's
``Content-Type`` is one of the following values:

* ``application/x-www-form-urlencoded``, ``multipart/form-data``

  The standard HTTP `POST` encoding; the key-value pairs are parsed
  exactly the same way as the query string, i.e. they are unflattened
  using FormEncode's `variable_decode` implementation. Note that for
  ``multipart/form-data`` (the content-type used for standard
  HTTP-based file uploading), nothing special is done: the `file`
  object that is in `request.POST` is simply referenced as-is in
  `request.input` as well.

* ``application/json``, ``application/x-json``, ``text/json``, ``text/x-json``, ``...+json``

  The payload is parsed using the built-in JSON parser, and no further
  processing is done. The data is required to be a dictionary unless
  the `pyramid_input.require-dict` is set to false, and if this is
  violated, request processing is aborted with a 400 "Bad Request"
  response error.

* ``application/yaml``, ``application/x-yaml``, ``text/yaml``, ``text/x-yaml``, ``...+yaml``

  If the `PyYAML` package is available, the payload is parsed using
  the YAML parser, and no further processing is done. The data is
  required to be a dictionary unless the `pyramid_input.require-dict`
  is set to false, and if this is violated, request processing is
  aborted with a 400 "Bad Request" response error.

* ``application/xml``, ``application/x-xml``, ``text/xml``, ``text/x-xml``, ``...+xml``

  The payload is parsed using the built-in ElementTree parser and the
  XML document is converted to a tree via a fairly simplistic mapping
  process. Note that this mapping process is "lossy", i.e. some
  aspects of the XML serialization (such as order of interleaved
  non-similar children nodes) are lost in the convertion.


Combination
===========

When both query string paramaters and a payload is specified in the
request, the output of parsing both data sources are then combined
together to form a single data tree. By default (i.e. when
`pyramid_input.combine.deep` is true), the payload data overrides the
query string data by overlaying and merging the two tree structures
recursively.

A recursive deep merge basically means that dict keys get merged with
dict keys, and all other type combinations turn into lists.

The deep merge can be disabled by setting the
`pyramid_input.combine.deep` option to false, in which case the
payload top-level dict keys completely override the query string
top-level keys, without any inspection of sub-keys.

For example, given the following query string tree structure:

.. code:: yaml

  foo: bar
  dict:
    list: [a, b]
    item: c

and the following payload tree structure:

.. code:: yaml

  bar: foo
  dict:
    list: d  
    item: e

a deep merge will result in:

.. code:: yaml

  foo: bar
  bar: foo
  dict:
    list: [a, b, d]
    item: [c, e]

and a non-deep merge will result in:

.. code:: yaml

  foo: bar
  bar: foo
  dict:
    list: d
    item: e


Configuration
=============

The following configuration settings can be set in your application's
``main`` section:

* ``pyramid_input.enabled`` : bool, default: true

* ``pyramid_input.attribute-name`` : str, default: 'input'

* ``pyramid_input.combine.deep`` : bool, default: true

* ``pyramid_input.include`` : list(glob), default: `/**`

* ``pyramid_input.exclude`` : list(glob), default: null

* ``pyramid_input.require-dict`` : bool, default: true

* ``pyramid_input.fail-unknown`` : bool, default: true

  If the request's Content-Type is unknown (or its parser disabled)
  and `pyramid_input.fail-unknown` is true, a 400 "bad request" error
  is returned.  If set to false, the payload is ignored.

* ``pyramid_input.native-dict`` : bool, default: false

  If true, `request.input` will be a standard python `dict` object.
  If false (the default), then it will be a recursive `aadict` object
  (which is a subclass of dict that supports attribute-based access to
  its items).

* ``pyramid_input.error-handler`` : symbol-spec, default: null

  On error (such as a 400 "Bad Request" for invalid JSON), this
  function is called with the `pyramid.httpexceptions.Exception`
  subclass that caused the error. The default implementation has
  this function signature equivalent:

  .. code:: python

    def function(request, error):
      return error

* ``pyramid_input.json.enable`` : bool, default: true

* ``pyramid_input.json.parser`` : symbol-spec, default: null

  Specifies the JSON parser. If not specified, uses Pyramid's
  pre-existing ``Request.json_body`` attribute.

* ``pyramid_input.yaml.enable`` : bool, default: true

* ``pyramid_input.yaml.parser`` : symbol-spec, default: 'yaml.load'

* ``pyramid_input.xml.enable`` : bool, default: true

* ``pyramid_input.xml.parser`` : symbol-spec, default: 'xml.etree.ElementTree.fromstring'
