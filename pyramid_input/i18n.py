# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# file: $Id$
# auth: Philip J Grabner <phil@canary.md>
# date: 2015/06/16
# copy: (C) Copyright 2015-EOT Canary Health, Inc., All Rights Reserved.
#------------------------------------------------------------------------------

from gettext import gettext

#------------------------------------------------------------------------------
def _(message, *args, **kw):
  if args or kw:
    return gettext(message).format(*args, **kw)
  return gettext(message)

#------------------------------------------------------------------------------
# end of $Id$
# $ChangeLog$
#------------------------------------------------------------------------------
