# -*- coding: utf-8 -*-
import ConfigParser

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
