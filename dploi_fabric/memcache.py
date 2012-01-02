SUPERVISOR_MEMCACHED_TEMPLATE = """
[program:{{ user }}_memcached]
command=memcached -s {{ project_path }}../tmp/memcached.sock
directory={{ project_path }}
user={{ user }}
autostart=True
autorestart=True
redirect_stderr=True
"""