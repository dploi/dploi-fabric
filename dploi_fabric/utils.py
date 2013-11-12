from dploi_fabric.toolbox.template import app_package_path, render_template
import os
import posixpath

import StringIO
from fabric.operations import run, local
from fabric.api import task, env, get
from fabric.contrib.files import exists
from fabric.state import _AttributeDict


from dploi_fabric.toolbox.datastructures import EnvConfigParser
from dploi_fabric.messages import DOMAIN_DICT_DEPRECATION_WARNING

STATIC_COLLECTED = "../static/"
DATA_DIRECTORY = "../upload/"

class Configuration(object):
    """
    This class is the only correct source of information for this project.
    To reduce the amount of times config.ini is downloaded, it should always
    be used from utils.config, which is an instance of Configuration
    """
    #: Default values for the configuration
    defaults = {
        'django': {
            'base': '.',
            'append_settings': False,
            'cmd': 'bin/django',
            'args': [],
        },
        'checkout': {
            'tool': 'buildout',
        },
        'gunicorn': {
            'workers': 2,
        },
        'celery': {
            'enabled': False,
            'concurrency': 1,
            'maxtasksperchild': 500,
            'loglevel': 'WARNING',
            'celerycam': False,
            'version': None,
            'app': 'project',
        },
        'static': {

        },
        'redis': {
            'enabled': False,
            'appendonly': 'no',
            'template': app_package_path('templates/redis/redis.conf'),
        },
        'processes': {

        },
        'sendfile': {

        },
        'environment': {

        },
        'nginx': {
            'client_max_body_size': '10m',
            'template': app_package_path('templates/nginx/nginx.conf'),
        },
        'supervisor': {
            'template': app_package_path('templates/supervisor/supervisor.conf'),
            'group_template': app_package_path('templates/supervisor/supervisor-group.conf'),
            'gunicorn_command_template': app_package_path('templates/supervisor/gunicorn_command'),
            'celeryd_command_template': app_package_path('templates/supervisor/celeryd_command'),
            'celerycam_command_template': app_package_path('templates/supervisor/celerycam_command'),
        },
        'newrelic': {
            'enabled': False,
            'config_file': 'newrelic.ini',
            'environment_name': '',
            'license': '',
        }
    }
    def load_sites(self, config_file_content=None, env_dict=None):
        """
        Called from self.sites and returns a dictionary with the different sites
        and their individual settings.
        """
        if not config_file_content:
            if env.get("use_local_config_ini", False):
                output = open("config.ini")
            else:
                config_file = os.path.join(env.path, "config.ini")
                if exists(config_file):
                    output = StringIO.StringIO()
                    get(u"%s" % config_file, output)
                    output.seek(0)
                else:
                    raise Exception("Missing config.ini, tried path %s" % config_file)
        else:
            output = StringIO.StringIO(config_file_content)

        if not env_dict:
            env_dict = env

        config = EnvConfigParser()
        config.readfp(output)
        self._sites = {}
        for site in config.section_namespaces("django") or ["main"]:
            attr_dict = self.defaults.copy()
            for key, value in attr_dict.items():
                attr_dict[key] = _AttributeDict(value.copy())
            for section in config.sections():
                section = section.split(":")[0]
                if self.defaults.get(section) is None:
                    print "Caution: Section %s is not supported, skipped" % section
                    continue
                for option, default_value in config.items(section, env=site):
                    setting = self.defaults.get(section).get(option)
                    if type(setting) == bool:
                        value = config.getboolean(section, option, env=site)
                    elif type(setting) == int:
                        value = config.getint(section, option, env=site)
                    elif type(setting) == float:
                        value = config.getfloat(section, option, env=site)
                    else:
                        variables = {
                            'static_collected': STATIC_COLLECTED,
                            'data_directory': DATA_DIRECTORY,
                        }
                        value = config.get(section, option, env=site) % variables
                    attr_dict[section][option] = value
            self.sites[site] = _AttributeDict(attr_dict)
            attr_dict.update(self.deployment(site, env_dict))
            if attr_dict.get("checkout").get("tool") == "buildout":
                # e.g. bin/django -> /home/username/app/bin/django
                attr_dict["django"]["cmd"] = posixpath.join(
                    attr_dict.get("deployment").get("path"),
                    attr_dict.get("django").get("cmd")
                )
            else:
                # e.g. manage.py -> /home/username/app/bin/python /home/username/app/manage.py
                new_django_cmd = [
                    posixpath.join(
                        attr_dict.get("deployment").get("path"),
                        "bin/python",
                    ),
                    posixpath.join(
                        attr_dict.get("deployment").get("path"),
                        attr_dict.get("django").get("base"),
                        attr_dict.get("django").get("cmd")
                    )
                ]
                attr_dict["django"]["cmd"] = " ".join(new_django_cmd)
                if attr_dict["django"]["append_settings"]:
                    attr_dict["django"]["args"].append(" --settings=%s" % ('_gen.settings', ))
            if attr_dict["newrelic"]["enabled"]:
                attr_dict["django"]["cmd"] = posixpath.join(
                    attr_dict.get("deployment").get("path"),
                    "bin/newrelic-admin"
                ) +  " run-program " + attr_dict["django"]["cmd"]
            attr_dict.update({'processes': self.processes(site, env_dict)})
            attr_dict['environment'] = self.environment(site, env_dict)
            attr_dict['environment'].setdefault('DEPLOYMENT_SITE', site)
            if attr_dict['deployment']['django_settings_module']:
                attr_dict['environment']['DJANGO_SETTINGS_MODULE'] = attr_dict['deployment']['django_settings_module']
            attr_dict['environment_export'] = self.build_environment_export(attr_dict['environment'])
            attr_dict['identifier'] = env_dict.identifier
            self._sites[site] = _AttributeDict(attr_dict)
        return self._sites

    def build_environment_export(self, environment):
        """
        takes a dict with environment variables and products a shell compatible export statement:
        'export PYTHONPATH="stuff/here:more/here" USER="mysite-dev";'
        """
        vars = " ".join([u'%s=%s' % (key, value) for key, value in environment.items()])
        return u"export %s;" % vars

    @property
    def sites(self):
        if getattr(self, "_sites", False) == False:
            self.load_sites()
        return self._sites

    def processes(self, site, env_dict):
        """
        Returns a dictionary of dictionaries each having the following keys:

        * command
            command to be run by supervisor
        * port
            port number,
        * socket
            path to unix socket
        * type
            gunicorn/memcached/celeryd
        """
        process_dict = {}
        site_dict = self.sites[site]
        common_cmd_context = {
            "django_cmd": site_dict.django['cmd'],
            "django_args": " ".join(site_dict.get("django").get("args", [])),
        }
        gunicorn_cmd_context = {
            "socket": posixpath.normpath(posixpath.join(env_dict.get("path"), "..", "tmp", "%s_%s_gunicorn.sock" % (env_dict.get("user"), site))), # Asserts pony project layout
            "workers": site_dict.gunicorn['workers'],
        }
        gunicorn_cmd_context.update(common_cmd_context)
        gunicorn_command_template_path = self.sites[site]['supervisor']['gunicorn_command_template']
        gunicorn_command = render_template(gunicorn_command_template_path, gunicorn_cmd_context)
        process_dict["%s_%s_gunicorn" % (env_dict.get("user"), site)] = {
                    'command': gunicorn_command,
                    'port': None,
                    'socket': gunicorn_cmd_context['socket'],
                    'type': 'gunicorn',
                    'priority': 100,
                }

        memcached_socket = posixpath.normpath(posixpath.join(env_dict.get("path"), "..", "tmp", "%s_%s_memcached.sock" % (env_dict.get("user"), site))) # Asserts pony project layout

        process_dict["%s_%s_memcached" % (env_dict.get("user"), site)] = {
                    'command': "memcached -s %s" % memcached_socket,
                    'port': None,
                    'socket': memcached_socket,
                    'type': 'memcached',
                    'priority': 60,
                }
        if site_dict.get("celery").get("enabled"):
            cmd = env_dict.get("path") if not site_dict.get("newrelic").get("enabled") else '%sbin/newrelic-admin run-program %s' % (env_dict.get("path"), env_dict.get("path"))
            cmd += 'bin/celery'
            celeryd_command_context = {
                'concurrency': site_dict.get("celery").get("concurrency"),
                'maxtasksperchild': site_dict.get("celery").get("maxtasksperchild"),
                'loglevel': site_dict.get("celery").get("loglevel"),
                'path': env_dict.get("path"),
                'version': site_dict.get("celery").get("version"),
                'celery_app': site_dict.get("celery").get("app"),
                'has_cam': site_dict.get("celery").get("celerycam"),
                'cmd': cmd,
            }
            celeryd_command_context.update(common_cmd_context)
            celeryd_command_template_path = self.sites[site]['supervisor']['celeryd_command_template']
            celeryd_command = render_template(celeryd_command_template_path, celeryd_command_context)
            process_dict["%s_%s_celeryd" % (env_dict.get("user"), site)] = {
                    'command': celeryd_command,
                    'port': None,
                    'socket': None,
                    'type': 'celeryd',
                    'priority': 40,
                }
            if site_dict.get("celery").get("celerycam"):
                celerycam_command_context = {
                    'loglevel': site_dict.get("celery").get("loglevel"),
                    'path': env_dict.get("path"),
                    'version': site_dict.get("celery").get("version"),
                    'celery_app': site_dict.get("celery").get("app"),
                    'cmd': cmd,
                }
                celerycam_command_context.update(common_cmd_context)
                celerycam_command_template_path = self.sites[site]['supervisor']['celerycam_command_template']
                celerycam_command = render_template(celerycam_command_template_path, celerycam_command_context)
                process_dict["%s_%s_celerycam" % (env_dict.get("user"), site)] = {
                    'command': celerycam_command,
                    'port': None,
                    'socket': None,
                    'type': 'celerycam',
                    'priority': 50,
                }
        if site_dict.get("redis").get("enabled"):
            process_name = "%s_%s_redis" % (env_dict.get("user"), site)
            redis_socket = posixpath.normpath(posixpath.join(env_dict.get("path"), "..", "tmp", process_name + ".sock" )) # Asserts pony project layout
            process_dict[process_name] = {
                'command': "/usr/bin/redis-server %s" % posixpath.normpath(posixpath.join(env_dict.get('path'), '..', 'config', process_name + '.conf')),
                'port': None,
                'socket': redis_socket,
                'type': 'redis',
                'priority': 20,
            }
        if site_dict.get('processes'):
            processes = site_dict.get('processes')
            for process, command in processes.iteritems():
                process_name = "%s_%s_process_%s" % (env_dict.get("user"), site, process)
                process_dict[process_name] = {
                    'command': posixpath.join(env_dict.get("path"), command),
                    'port': None,
                    'socket': None,
                    'type': 'supervisor',
                    'priority': env_dict.get("priority", 200),
                }

        return process_dict

    def environment(self, site, env_dict):
        site_dict = self.sites[site]
        return site_dict['environment']

    def deployment(self, site, env_dict):
        """
        Here we add the information from deployments.py and merge it into our site dictionaries.
        Can also be used to output warnings to the user, if he is using an old deployments.py
        format.
        """
        deployment_dict = {
            # Old settings
            'servername': env_dict.get("host_string"),
            'path': env_dict.get("path"),
            'backup_dir': env_dict.get("backup_dir"),
            'repo': env_dict.get("repo"),
            'branch': env_dict.get("branch"),
            'user': env_dict.get("user"),
            'buildout_cfg': env_dict.get("buildout_cfg"),
            'django_settings_module': env_dict.get("django_settings_module"),
            'generated_settings_path': posixpath.join(env_dict.get("path"), "_gen/settings.py"),

            # New settings
            'domains_redirect': env_dict.get('domains_redirect'),
            'url_redirect': env_dict.get('url_redirect'),

            'basic_auth': env_dict.get('basic_auth', False),
            'basic_auth_path': os.path.join(env_dict.get("path"), env_dict.get('basic_auth_path', None) or ""),

            'ssl': env.get('ssl', False),
            'ssl_cert_path': os.path.join(env_dict.get("path"), env_dict.get('ssl_cert_path', None) or ""),
            'ssl_key_path': os.path.join(env_dict.get("path"), env_dict.get('ssl_key_path', None) or ""),
            'bind_ip': env_dict.get('bind_ip', '*'),
            'static_error_pages': env_dict.get('static_error_pages', []),
            'big_body_endpoints': env_dict.get('big_body_endpoints', []),
            'home': '/home/%s' %  env_dict.get("user"),
        }

        if not env_dict.get("databases"):
            deployment_dict["databases"] = {
                'default': {
                    'ENGINE': env_dict.get("db_engine", "django.db.backends.postgresql_psycopg2"),
                    'NAME': env_dict.get("db_name"),
                    'USER': env_dict.get("db_username"),
                    'PASSWORD': env_dict.get("db_password"),
                    'HOST': env_dict.get("db_host", ""),
                }
            }

        if type(env_dict.get("domains")) == list:
            domains = {
                "main": env_dict.get("domains"),
            }
            print(DOMAIN_DICT_DEPRECATION_WARNING)
        elif type(env_dict.get("domains")) == dict:
            domains = env_dict.get("domains")
        elif env_dict.get("domains") is None:
            domains = {
                "main": [],
            }
            print("Warning: No domains supplied in settings, ignoring.")
        else:
            raise Exception("Invalid domain format")
        deployment_dict.update({'domains': domains})

        ###############
        # Environment #
        ###############

        environment_dict = self.sites[site].get("environment")
        for key, value in env_dict.get("environment", {}).items():
            environment_dict[key] = value

        #################
        # Gunicorn dict #
        #################
        gunicorn_dict = self.sites[site].get("gunicorn")
        gunicorn_dict["workers"] = env_dict.get("gunicorn", {}).get("workers", gunicorn_dict.get("workers"))

        ###############
        # Celery dict #
        ###############
        celery_dict = self.sites[site].get("celery")

        celery_dict["concurrency"] = env_dict.get("celery", {}).get("concurrency", celery_dict.get("concurrency"))
        celery_dict["maxtasksperchild"] = env_dict.get("celery", {}).get("maxtasksperchild", celery_dict.get("maxtasksperchild"))

        ##############
        # nginx dict #
        ##############

        nginx_dict = self.sites[site].get("nginx")
        nginx_dict["location_settings"] = {
            "client_max_body_size": env_dict.get("nginx", {}).get("client_max_body_size", nginx_dict.get("client_max_body_size")),
        }
        nginx_dict["template"] = env_dict.get("nginx", {}).get("template", nginx_dict.get("template"))

        ##############
        # redis dict #
        ##############

        redis_dict = self.sites[site].get("redis")
        redis_dict["template"] = env_dict.get("redis", {}).get("template", redis_dict.get("template"))

        ###################
        # supervisor dict #
        ###################

        supervisor_dict = self.sites[site].get("supervisor")
        supervisor_dict["template"] = env_dict.get("supervisor", {}).get("template", supervisor_dict.get("template"))
        supervisor_dict["group_template"] = env_dict.get("supervisor", {}).get("group_template", supervisor_dict.get("group_template"))
        supervisor_dict["gunicorn_command_template"] = env_dict.get("supervisor", {}).get("gunicorn_command_template", supervisor_dict.get("gunicorn_command_template"))
        supervisor_dict["celeryd_command_template"] = env_dict.get("supervisor", {}).get("celeryd_command_template", supervisor_dict.get("celeryd_command_template"))
        supervisor_dict["celerycam_command_template"] = env_dict.get("supervisor", {}).get("celerycam_command_template", supervisor_dict.get("celerycam_command_template"))

        #################
        # newrelic dict #
        #################

        newrelic_dict = self.sites[site].get("newrelic")
        newrelic_dict["enabled"] = env_dict.get("newrelic", {}).get("enabled", newrelic_dict.get("enabled"))
        newrelic_dict["config_file"] = env_dict.get("newrelic", {}).get("config_file", newrelic_dict.get("config_file"))
        if not newrelic_dict["config_file"].startswith('/'):
            newrelic_dict["config_file"] = posixpath.abspath(posixpath.join(
                    deployment_dict["path"],
                    newrelic_dict["config_file"],
                ))
        self.sites[site]["environment"]["NEW_RELIC_CONFIG_FILE"] = newrelic_dict["config_file"]
        newrelic_dict["environment_name"] = env_dict.get("newrelic", {}).get("environment_name", newrelic_dict.get("environment_name"))
        if newrelic_dict["environment_name"]:
            self.sites[site]["environment"]["NEW_RELIC_ENVIRONMENT"] = newrelic_dict["environment_name"]

        newrelic_dict["license_key"] = env_dict.get("newrelic", {}).get("license_key", newrelic_dict.get("license_key"))
        if newrelic_dict["license_key"]:
            self.sites[site]["environment"]["NEW_RELIC_LICENSE_KEY"] = newrelic_dict["license_key"]

        return {
            'deployment': deployment_dict,
            'environment': environment_dict,
            'gunicorn': gunicorn_dict,
            'celery': celery_dict,
            'nginx': nginx_dict,
            'redis': redis_dict,
            'supervisor': supervisor_dict,
            'newrelic': newrelic_dict,
        }

    def django_manage(self, command, site="main"):
        """
        Wrapper around the commands to inject the correct pythonpath.

        Example: django_manage("migrate"), could result in

        export PYTONPATH=/home/app-dev/app/; /home/app-dev/app/bin/python /home/app-dev/app/manage.py migrate
        """
        site_dict = config.sites[site]
        cmd = site_dict.get("django").get("cmd")
        django_args = " ".join(site_dict.get("django").get("args", []))
        run('%s %s %s %s' % (site_dict['environment_export'], cmd, command, django_args))

if not __name__ == '__main__':
    #: A shared instance of configuration, always to be used
    config = Configuration()


@task
def check_config():
    for section in config_ini.config_parser.sections():
        print "[%s]" % section
        print config_ini.config_parser.items(section)

@task
def uname():
    print env.host_string
    run('uname -a')

@task
def ls():
    run('cd %(path)s;ls -lAF' % env)

@task
def ps():
    """
    show processes of this user
    """
    run('ps -f -u %(user)s | grep -v "ps -f" | grep -v sshd' % env)

@task
def download_media(to_dir="./tmp/media/", from_dir="../upload/media/"):
    """
    Downloads media from a remote folder, default ../uploads/ -> ./tmp/media/

    * Example: upload_media:from_dir="py_src/project/media/"
    """
    print "Downloading media from", env.host_string
    env.from_dir = from_dir
    local('rsync -avz --no-links --progress --exclude=".svn" -e "ssh" %(user)s@%(host_string)s:"%(path)s/%(from_dir)s"' % env + " " +to_dir)

@task
def upload_media(from_dir="./tmp/media/", to_dir="../upload/media/"):
    """
    Uploads media from a local folder, default ./tmp/media -> ../uploads/
    
    * Example: upload_media:to_dir="py_src/project/media/"
    """
    print "Uploading media to", env.host_string
    env.to_dir = to_dir
    local('rsync -avz --no-links --progress --exclude=".svn" '+ from_dir +' -e "ssh" %(user)s@%(host_string)s:"%(path)s/%(to_dir)s"' % env)


@task
def use_local_config_ini():
    env.use_local_config_ini = True