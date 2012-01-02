import datetime
from fabric.api import env, run, get
from fabric.tasks import Task

class DumpDatabaseTask(object):
    def get_path(self, env, reason):
        mytimestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')
        reason = reason.replace(' ', '_')
        return ('%(backup_dir)s/%(db_name)s-' + mytimestamp + '-' + reason + '.sql') % env

    def get_command(self, env, file_name):
        raise NotImplementedError

    def run(self, reason='unknown', compress=False):
        file_name = self.get_path(env, reason)
        command = self.get_command(env, file_name)
        run(command)
        if compress:
            run('gzip ' + file_name)
            file_name += '.gz'
        return file_name


class DownloadDatabase(Task):
    """
    Download the database
    """

    name = 'download'

    def __init__(self, dump_task):
        self.dump_task = dump_task

    def run(self, path='tmp'):
        file_name = self.dump_task.run(reason='for_download', compress=True, nolock=True)
        get(file_name, path)