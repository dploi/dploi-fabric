# -*- coding: utf-8 -*-
import sys
import subprocess
from functools import wraps

from fabric.api import task, env, prompt
from fabric.operations import run

from toolbox import logger


logged_output = {'stdout': "", 'stderr': ""}


class log_output():
    def __init__(self):
        global logged_output
        self.stdout_logger = logger.Logger(sys.stdout)
        self.stderr_logger = logger.Logger(sys.stderr)
        sys.stdout = self.stdout_logger
        sys.stderr = self.stderr_logger

    def __enter__(self):
        self.stdout_logger.clear()
        self.stderr_logger.clear()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # TODO: Add exception handling?
        logged_output['stdout'] += self.stdout_logger.get_log()
        logged_output['stderr'] += self.stderr_logger.get_log()


def register_deployment(func):
    @wraps(func)
    def with_logging(*args, **kwargs):
        hash_before = run("cd %(path)s; git --no-pager log -1 --oneline %(branch)s --pretty='%%h'" % env)
        if hash_before == "":
            hash_before = False

        __func_ret = func(*args, **kwargs)

        try:
            handle = subprocess.check_output(["git", "config", "--get", "github.user"]).strip()
        except subprocess.CalledProcessError:
            handle = prompt("Please enter your GitHub username:")

        try:
            email = subprocess.check_output(["git", "config", "--get", "user.email"]).strip()
        except subprocess.CalledProcessError:
            email = prompt("Please enter your email address:")

        user = "%s (%s)" % (handle, email)

        log_base = "cd app && git --no-pager log -1 --oneline"
        commit_hash = run(log_base + " --pretty=%h")
        commit_message = run(log_base + " --pretty=%s")
        commit_author_name = run(log_base + " --pretty=%aN")

        if hash_before and hash_before != commit_hash:
            diff_url = "https://%s/compare/%s...%s" % (run("cd app && git config --get remote.origin.url").replace(
                "git@", "", 1).replace(":", "/", 1).replace(".git", "", 1), hash_before, commit_hash)
            msg = "%s from %s (%s)" % (commit_message, commit_author_name, diff_url)

        else:
            url = "https://%s/commit/%s" % (run("cd app && git config --get remote.origin.url").replace(
                "git@", "", 1).replace(":", "/", 1).replace(".git", "", 1), commit_hash)

            if hash_before and hash_before == commit_hash:
                msg = "No changes in the repository. %s" % url

            else:
                msg = "No pre-pull commit hash provided. %s" % url

        log = logged_output['stdout']
        if logged_output['stderr']:
            log += "\nErrors:\n%s" % str(logged_output['stderr'])

        options = {'app_name': env['user'], 'user': user, 'description': msg, 'revision': commit_hash, 'changelog': log}

        cmd = 'curl -H "x-api-key:%s"' % env['newrelic']['deployment_tracking_apikey']

        for key, val in options.items():
            cmd += ' --data-urlencode "deployment[%s]=%s"' % (key, val)

        cmd += " https://rpm.newrelic.com/deployments.xml"
        subprocess.call(cmd, shell=True)
        return __func_ret
    return with_logging
