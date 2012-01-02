import ConfigParser
import StringIO
from fabric.operations import run, local
from fabric.api import task, env, get
import os
from fabric.contrib.files import exists
import unittest
import posixpath
from .messages import DOMAIN_DICT_DEPRECATION_WARNING, EXCEPTION

STATIC_COLLECTED = "../static/"
DATA_DIRECTORY = "../uploads/"


class EnvConfigParser(ConfigParser.SafeConfigParser):
    """ A config parser that can handle "namespaced" sections. Example:

    [base]
    name = base

    [base:some-env]
    name = some-env

    """

    def _concat(self, parent, child):
        return '%s:%s' % (parent, child)

    def items(self, section, raw=False, vars=None, env=None):
        items = {}
        try:
            items.update(dict(ConfigParser.SafeConfigParser.items(self, section, raw, vars)))
        except ConfigParser.NoSectionError:
            pass
        if env:
            try:
                env_items = dict(ConfigParser.SafeConfigParser.items(self, self._concat(section, env), raw, vars))
                items.update(env_items)
            except ConfigParser.NoSectionError:
                pass
        if not items:
            raise ConfigParser.NoSectionError(self._concat(section, env) if env else section)
        return tuple(items.iteritems())

    def get(self, section, option, raw=False, vars=None, env=None):
        if env and self.has_section(self._concat(section, env)):
            try:
                return ConfigParser.SafeConfigParser.get(self, self._concat(section, env), option, raw, vars)
            except ConfigParser.NoOptionError:
                if not self.has_section(section):
                    raise
        return ConfigParser.SafeConfigParser.get(self, section, option, raw, vars)

    def _get(self, section, conv, option, env=None):
        return conv(self.get(section, option, env=env))

    def getint(self, section, option, env=None):
        return self._get(section, int, option, env)

    def getfloat(self, section, option, env=None):
        return self._get(section, float, option, env)

    def getboolean(self, section, option, env=None):
        v = self.get(section, option, env=env)
        if v.lower() not in self._boolean_states:
            raise ValueError, 'Not a boolean: %s' % v
        return self._boolean_states[v.lower()]

    def has_section(self, section, env=None, strict=False):
        if not env:
            return ConfigParser.SafeConfigParser.has_section(self,section)
        return (
            (not strict and ConfigParser.SafeConfigParser.has_section(self, section)) or
            ConfigParser.SafeConfigParser.has_section(self, self._concat(section, env))
        )

    def section_namespaces(self, section):
        namespaces = []
        for s in self.sections():
            s = s.split(":")
            if s[0] == section:
                if len(s) == 1:
                    namespaces.append("main")
                else:
                    namespaces.append(s[1])
        return namespaces

    def _interpolate(self, section, option, rawval, vars):
        return rawval


class _AttributeDict(dict):
    """
    Dictionary subclass enabling attribute lookup/assignment of keys/values.

    For example::

        >>> m = _AttributeDict({'foo': 'bar'})
        >>> m.foo
        'bar'
        >>> m.foo = 'not bar'
        >>> m['foo']
        'not bar'

    ``_AttributeDict`` objects also provide ``.first()`` which acts like
    ``.get()`` but accepts multiple keys as arguments, and returns the value of
    the first hit, e.g.::

        >>> m = _AttributeDict({'foo': 'bar', 'biz': 'baz'})
        >>> m.first('wrong', 'incorrect', 'foo', 'biz')
        'bar'

    """
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            # to conform with __getattr__ spec
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def first(self, *names):
        for name in names:
            value = self.get(name)
            if value:
                return value

class Configuration(object):
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
        'celery': {
            'enabled': False,
            'concurrency': 1,
            'maxtasksperchild': 500,
        },
        'static': {

        },
    }
    def load_sites(self, config_file_content=None, env_dict=None):
        if not config_file_content:
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
                if type(self.defaults.get(section)) == type(None):
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

            attr_dict.update({'processes': self.processes(site, env_dict)})
            self._sites[site] = _AttributeDict(attr_dict)
        return self._sites

    @property
    def sites(self):
        if getattr(self, "_sites", False) == False:
            self.load_sites()
        return self._sites

    def processes(self, site, env_dict):
        process_dict = {}
        site_dict = self.sites[site]
        django_args = " ".join(site_dict.get("django").get("args", []))
        gunicorn_socket = posixpath.join(env_dict.get("path"), "..", "tmp", "%s_%s_gunicorn.sock" % (env_dict.get("user"), site)) # Asserts pony project layout

        process_dict["%s_%s_gunicorn" % (env_dict.get("user"), site)] = {
                    'command': "%s run_gunicorn -w 2 -b unix:%s %s" % (site_dict.django['cmd'], gunicorn_socket, django_args),
                    'port': None,
                    'socket': gunicorn_socket,
                    'type': 'gunicorn'
                }

        memcached_socket = posixpath.join(env_dict.get("path"), "..", "tmp", "%s_%s_memcached.sock" % (env_dict.get("user"), site)) # Asserts pony project layout

        process_dict["%s_%s_memcached" % (env_dict.get("user"), site)] = {
                    'command': "memcached -s %s" % memcached_socket,
                    'port': None,
                    'socket': memcached_socket,
                    'type': 'memcached'
                }
        if site_dict.get("celery").get("enabled"):
            process_dict["%s_%s_celeryd" % (env_dict.get("user"), site)] = {
                    'command': "%s celeryd -E -B -c %s --maxtasksperchild %s %s" % (site_dict.django['cmd'], site_dict.get("celery").get("concurrency"), site_dict.get("celery").get("maxtasksperchild"), django_args),
                    'port': None,
                    'socket': None,
                    'type': 'celeryd'
                }
        return process_dict

    def deployment(self, site, env_dict):

        ###################
        # Deployment dict #
        ###################
        deployment_dict = {
            # Old settings
            'servername': env_dict.get("host_string"),
            'path': env_dict.get("path"),
            'backup_dir': env_dict.get("backup_dir"),
            'repo': env_dict.get("repo"),
            'branch': env_dict.get("branch"),
            'user': env_dict.get("user"),
            'buildout_cfg': env_dict.get("buildout_cfg"),
            'generated_settings_path': posixpath.join(env_dict.get("path"), "_gen/settings.py"),

            # New settings
            'domains_redirect': env_dict.get('domains_redirect'),
            'url_redirect': env_dict.get('url_redirect'),

            'basic_auth': env_dict.get('basic_auth', False),
            'basic_auth_path': os.path.join(env_dict.get("path"), env_dict.get('basic_auth_path', None) or ""),

            'ssl': env.get('ssl', False),
            'ssl_cert_path': os.path.join(env_dict.get("path"), env_dict.get('ssl_cert_path', None) or ""),
            'ssl_key_path': os.path.join(env_dict.get("path"), env_dict.get('ssl_key_path', None) or ""),
        }

        if not env_dict.get("databases"):
            deployment_dict["databases"] = {
                'default': {
                    'ENGINE': "django.db.backends.postgresql_psycopg2",
                    'NAME': env_dict.get("db_name"),
                    'USER': env_dict.get("db_username"),
                }
            }

        if type(env_dict.get("domains")) == list:
            domains = {
                "main": env_dict.get("domains"),
            }
            print(DOMAIN_DICT_DEPRECATION_WARNING)
        elif type(env_dict.get("domains")) == dict:
            domains = env_dict.get("domains")
        else:
            raise Exception("Invalid domain format")
        deployment_dict.update({'domains': domains})

        ###############
        # Celery dict #
        ###############

        celery_dict = self.sites[site].get("celery")

        celery_dict["concurrency"] = env_dict.get("celery", {}).get("concurrency", celery_dict.get("concurrency"))
        celery_dict["maxtasksperchild"] = env_dict.get("celery", {}).get("maxtasksperchild", celery_dict.get("maxtasksperchild"))


        return {'deployment': deployment_dict, 'celery': celery_dict}

    def django_manage(self, command, site="main"):
        site_dict = config.sites[site]
        cmd = site_dict.get("django").get("cmd")
        django_args = " ".join(site_dict.get("django").get("args", []))
        run('export PYTHONPATH=%s; %s %s %s' % (site_dict.get("deployment").get("path"), cmd, command, django_args))

if not __name__ == '__main__':
    config = Configuration()


@task
def check_config():
    for section in config_ini.config_parser.sections():
        print "[%s]" % section
        print config_ini.config_parser.items(section)

@task
def uname():
    print env.hosts
    from pprint import pprint
    pprint(env)
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
def download_media(to_dir="./tmp/media/", from_dir="../upload/"):
    """
    Downloads media from a remote folder, default ../uploads/ -> ./tmp/media/
    Example: upload_media:from_dir="py_src/project/media/"
        """
    print "Downloading media from", env.host_string
    env.from_dir = from_dir
    local('rsync -avz --no-links --progress --exclude=".svn" -e "ssh" %(user)s@%(host_string)s:"%(path)s/%(from_dir)s"' % env + " " +to_dir)

@task
def upload_media(from_dir="./tmp/media/", to_dir="../upload/"):
    """
    Uploads media from a local folder, default ./tmp/media -> ../uploads/
    Example: upload_media:to_dir="py_src/project/media/"
    """
    print "Uploading media to", env.host_string
    env.to_dir = to_dir
    local('rsync -avz --no-links --progress --exclude=".svn" '+ from_dir +' -e "ssh" %(user)s@%(host_string)s:"%(path)s/%(to_dir)s"' % env)
