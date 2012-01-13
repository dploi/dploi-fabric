import StringIO
from fabric.decorators import task
from fabric.api import run, env, put

from dploi_fabric.toolbox.template import render_template
from dploi_fabric.utils import config


@task(alias="reload")
def reload_nginx():
    run('sudo /etc/init.d/nginx reload')
    
@task
def update_config_file():
    output = ""
    template_name = 'templates/nginx/nginx.conf'
    for site, site_config in config.sites.items():
        context_dict = site_config
        context_dict.update({
            'domains': " ".join(site_config.deployment.get("domains")[site]),
            'www_processes': [site_config.processes[x] for x in site_config.processes if site_config.processes[x]["type"] == "gunicorn"],
        })

        output += render_template(template_name, context_dict)
    put(StringIO.StringIO(output), '%(path)s/../config/nginx.conf' % env)
    reload_nginx()
