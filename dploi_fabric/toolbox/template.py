# -*- coding: utf-8 -*-
import os

from django.conf import settings
from django.template import Template
from django.template.context import Context

import dploi_fabric

settings.configure(DEBUG=True, TEMPLATE_DEBUG=True)

def render_template(path, context):
    path = os.path.join(os.path.dirname(dploi_fabric.__file__), path)
    if not isinstance(context, Context):
        context = Context(context)
    template_file = open(path)
    template = Template(template_file.read())
    return template.render(context)