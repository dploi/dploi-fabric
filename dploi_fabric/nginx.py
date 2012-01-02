import StringIO
from fabric.decorators import task
from fabric.api import run, env, put
from django.template import Context, Template
from django.conf import settings
from .utils import config
settings.configure(DEBUG=True, TEMPLATE_DEBUG=True)

NGINX_TEMPLATE = """
upstream {{ domains|slugify }} {
{% for process in www_processes %}
    server unix:{{ process.socket}} fail_timeout=0;
{% endfor %}
}
server {
    {% if deployment.ssl %}
    listen  443;
    ssl on;
    ssl_certificate         {{ deployment.ssl_cert_path }};
    ssl_certificate_key     {{ deployment.ssl_key_path }};
    {% else %}
    listen  80;
    {% endif %}
    server_name  {{ domains }};

    access_log {{ deployment.path }}../log/nginx/access.log;
    error_log {{ deployment.path }}../log/nginx/error.log;

    location / {
        proxy_pass http://{{ domains|slugify }};
        proxy_redirect              off;
        proxy_set_header            Host $host;
        proxy_set_header            X-Real-IP $remote_addr;
        proxy_set_header            X-Forwarded-For $proxy_add_x_forwarded_for;
        client_max_body_size        10m;
        client_body_buffer_size     128k;
        proxy_connect_timeout       90;
        proxy_send_timeout          90;
        proxy_read_timeout          90;
        proxy_buffer_size           4k;
        proxy_buffers               4 32k;
        proxy_busy_buffers_size     64k;
        proxy_temp_file_write_size  64k;
        {% if deployment.ssl %}
        proxy_set_header X-Forwarded-Protocol https;
        proxy_set_header X-Forwarded-SSL on;
        {% else %}
        proxy_set_header X-Forwarded-Protocol http;
        proxy_set_header X-Forwarded-SSL off;
        {% endif %}
    }
    {% for url, relpath in static.items %}
    location  {{ url }} {
                 access_log off;
                 alias {{ deployment.path }}{{ relpath }};
    }
    {% endfor %}

    {% for redirect in deployment.url_redirect %}
    rewrite {{ redirect.source }} {{ redirect.destination }} {{ redirect.options|default:"permanent" }};
    {% endfor %}

    {% if deployment.basic_auth %}
    auth_basic            "Restricted";
    auth_basic_user_file  {{ basic_auth_path }};
    {% endif %}
}
{% if deployment.ssl %}
server {
    listen 80;
    server_name {{ domains }};
    rewrite ^(.*) https://$host$1 permanent;
}
{% endif %}
{% for redirect in deployment.domains_redirect %}
server {
    listen 80;
    server_name {{ redirect.domain }};
    rewrite ^(.*) http://{{ redirect.destination_domain }}$1 permanent;
    access_log {{ deployment.path }}../log/nginx/access.log;
    error_log {{ deployment.path }}../log/nginx/error.log;
}
{% endfor %}
"""

@task(alias="reload")
def reload_nginx():
    run('sudo /etc/init.d/nginx reload')
    
@task
def update_config_file():
    output = ""
    template = Template(NGINX_TEMPLATE)
    for site, site_config in config.sites.items():
        context_dict = site_config
        context_dict.update({
            'domains': " ".join(site_config.deployment.get("domains")[site]),
            'www_processes': [site_config.processes[x] for x in site_config.processes if site_config.processes[x]["type"] == "gunicorn"],
        })
        context = Context(context_dict)
        output += template.render(context)

    put(StringIO.StringIO(output), '%(path)s/../config/nginx.conf' % env)
    reload_nginx()
