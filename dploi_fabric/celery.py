from .utils import config_ini

celery_processes = ["celeryd", "celerybeat", "celerycam"]

SUPERVISOR_CELERY_TEMPLATE = """
[program:{{ user }}_celeryd]
command={{ django_exec }} celeryd -E
directory={{ project_path }}
user={{ user }}
autostart=True
autorestart=True
redirect_stderr=True

[program:{{ user }}_celerybeat]
command={{ django_exec }} celerybeat
directory={{ project_path }}
user={{ user }}
autostart=True
autorestart=True
redirect_stderr=True

[program:{{ user }}_celerycam]
command={{ django_exec }} celerycam
directory={{ project_path }}
user={{ user }}
autostart=True
autorestart=True
redirect_stderr=True

"""

def use_celery():
    return config_ini.config_parser.has_section("celery")