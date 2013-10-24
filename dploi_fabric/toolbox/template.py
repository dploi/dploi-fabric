# -*- coding: utf-8 -*-
import os

from django.conf import settings
from django.template import Template
from django.template.context import Context

import dploi_fabric

settings.configure(DEBUG=True, TEMPLATE_DEBUG=True)

def render_template(path, context):
    if not isinstance(context, Context):
        context = Context(context)
    with open(path) as template_file:
        template = Template(template_file.read())
    return template.render(context)


def app_package_path(path):
    """
    returns the abs path with the dploi_fabric package as base
    """
    return os.path.abspath(os.path.join(os.path.dirname(dploi_fabric.__file__), path))
