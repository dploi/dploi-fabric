import StringIO
from copy import copy
from fabric.decorators import task
from fabric.api import run, put, env
from dploi_fabric.toolbox.template import render_template
from dploi_fabric.utils import config, safe_put
import posixpath


@task
def stop():
    for site, site_config in config.sites.items():
        run('%s stop %s:*' % (site_config['supervisor']['supervisorctl_command'], get_group_name(site, site_config)))


@task
def start():
    for site, site_config in config.sites.items():
        run('%s start %s:*' % (site_config['supervisor']['supervisorctl_command'], get_group_name(site, site_config)))


@task
def restart():
    for site, site_config in config.sites.items():
        run('%s restart %s:*' % (site_config['supervisor']['supervisorctl_command'], get_group_name(site, site_config)))


@task
def status():
    """
    print status of the supervisor process

    Note: "status" does not yet support the group syntax
    """
    for site, site_config in config.sites.items():
        group_name = get_group_name(site, site_config)
        for process_name, process_cmd in site_config.processes.items():
            run('%s status %s:%s' % (site_config['supervisor']['supervisorctl_command'], group_name, process_name))


@task
def add():
    for site, site_config in config.sites.items():
        group_name = get_group_name(site, site_config)
        for process_name, process_cmd in site_config.processes.items():
            run('%s add %s:%s' % (site_config['supervisor']['supervisorctl_command'], group_name, process_name))


@task
def update():
    for site, site_config in config.sites.items():
        group_name = get_group_name(site, site_config)
        for process_name, process_cmd in site_config.processes.items():
            run('%s update %s:%s' % (site_config['supervisor']['supervisorctl_command'], group_name, process_name))


def get_group_name(site, site_config):
    return '%s-%s' % (site_config['deployment']['user'], site)


@task
def update_config_file(dryrun=False, update_command=update, load_config=True):
    output = ''
    groups = {}
    for site, site_config in config.sites.items():
        template_path = site_config['supervisor']['template']
        group_template_path = site_config['supervisor']['group_template']
        group_name = get_group_name(site, site_config)
        groups[group_name] = []
        for process_name, process_dict in site_config.processes.items():
            context_dict = copy(site_config)
            env_dict = {
                'HOME': site_config.deployment['home'],
                'USER': site_config.deployment['user'],
                'PYTHONPATH': ":".join([
                    site_config.deployment['path'],
                    posixpath.join(site_config.deployment['path'], site_config.get("django").get("base")+'/'),
                ]),
            }
            env_dict.update(site_config.environment)
            context_dict.update({
                'process_name': process_name,
                'process_cmd': process_dict["command"],
                'socket': process_dict["socket"],
                'env': env_dict,
                'priority': process_dict.get('priority', 200),
                'autostart': 'True' if getattr(env, 'autostart', True) else 'False',
                'killasgroup': process_dict.get('killasgroup', None),
                'stopasgroup': process_dict.get('killasgroup', None),
                'stopwaitsecs': process_dict.get('stopwaitsecs', None),
            })
            output += render_template(template_path, context_dict)
            groups[group_name].append(process_name)
    output += render_template(group_template_path, {'groups': groups})
    conf_path = posixpath.abspath(posixpath.join(config.sites["main"].deployment['path'], '..', 'config'))
    path = posixpath.join(conf_path, 'supervisor.conf')

    daemon_template_path = site_config['supervisor']['daemon_template']
    supervisord_conf_path = posixpath.join(conf_path, 'supervisord.conf')
    supervisord_conf_output = render_template(daemon_template_path, copy(site_config))

    if dryrun:
        print path + ':'
        print output
        print daemon_template_path + ':'
        print supervisord_conf_output
    else:
        safe_put(StringIO.StringIO(output), path)
        safe_put(StringIO.StringIO(supervisord_conf_output), supervisord_conf_path)
        if load_config:
            update_command()
