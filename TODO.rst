====
ToDo
====


* Currently, the `request.input` is populated before the request
  handler is invoked. Ideally, this should only be done when there is
  a request for the attribute. Unfortunately, that can only be done if
  `request.input` is made a descriptor, which can only be done if it
  is made into a class attribute, which means that it is polluting the
  global `Request` namespace.
  ==> implement this but make it optional (and by default disabled)!
  ==> or, better yet, find a solution that does not involve polluting
      the global namespace.
