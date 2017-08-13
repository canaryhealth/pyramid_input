======
TODO's
======

* add support to transparently convert a multipart/form-data (ie.
  file-upload) into request.input

* rename to ``pyramid-io``?
  ==> then merge with `pyramid-methodrewrite`?
  ==> and provide some basic support for response formatting support,
    * data => json
    * data => yaml
    * data => xml
    * data => csv // tablib
    * data => generic plugin+mimetype-based-support
      ==> pre-emptively load all plugins to see which ones can be
          loaded (eg. yaml requires PyYAML, so if not present, don't
          support) ==> which will register 
  ==> support other "helpers"...
    * _method=delete     == X-HTTP-Method-Override: delete
    * _status=200        == X-HTTP-Status-Override: 200
    * _xhr=1             == X-Requested-With: XMLHttpRequest
    * _accept=text/json  == Accept: text/json; q=1

* Currently, the `request.input` is populated before the request
  handler is invoked. Ideally, this should only be done when there is
  a request for the attribute. Unfortunately, that can only be done if
  `request.input` is made a descriptor, which can only be done if it
  is made into a class attribute, which means that it is polluting the
  global `Request` namespace.
  ==> implement this but make it optional (and by default disabled)!
  ==> or, better yet, find a solution that does not involve polluting
      the global namespace.

* move to use asset.plugins for the various content-type handlers
