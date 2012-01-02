import os

from fabric.api import env, task, prompt, run, get
from fabric.contrib import files
import getpass
import json
import urllib2
import subprocess
import StringIO
import requests

@task
def upload_ssh_deploy_key():
    if not files.exists("/home/%(user)s/.ssh/id_rsa.pub" % env):
        if not files.exists("/home/%(user)s/.ssh/"):
            run("mkdir -p /home/%(user)s/.ssh/" % env)
        run("ssh-keygen -t rsa -f '/home/%(user)s/.ssh/id_rsa' -P ''" % env)

    output = StringIO.StringIO()
    get("/home/%(user)s/.ssh/id_rsa.pub" % env, output)
    output.seek(0)
    
    ssh_key = output.read()

    logged_in = False
    while not logged_in:
        try:
            default_username = subprocess.check_output(["git", "config", "--get", "github.user"]).strip()
        except Exception:
            default_username = ''
        username = prompt("Please enter your GitHub username:", default=default_username)
        password = getpass.getpass("Please enter your GitHub password: ")

        repository = env.repo.rsplit(":", 1)[-1].replace(".git", "")
        response = json.loads(requests.get("https://api.github.com/repos/%s/keys" % repository, auth=(username, password), ).content)

        if 'message' in response:
            print(response['message'])
        else:
            logged_in = True
    
    match = [x for x in response if x.get("key") in ssh_key]
    if not match:
        data = {'key': ssh_key}
        data = json.dumps(data)
        requests.post("https://api.github.com/repos/%s/keys" % repository, auth=(username, password), data=data)