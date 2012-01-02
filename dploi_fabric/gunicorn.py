SUPERVISOR_GUNICORN_TEMPLATE = """
[program:{{ user }}_gunicorn]
command={{ django_exec }} run_gunicorn -w {{ web_workers }} -b unix:{{ project_path }}../tmp/gunicorn.sock
directory={{ project_path }}../
user={{ user }}
autostart=True
autorestart=True
redirect_stderr=True
"""