import datetime
from fabric.api import env, run, get
from fabric.tasks import Task
import os

class DumpDatabaseTask(object):
    def get_path(self, env, reason):
        mytimestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')
        reason = reason.replace(' ', '_')
        return os.path.join('%(backup_dir)s'  % env, '%(db_name)s-' % env + mytimestamp + '-' + reason + '.sql')

    def get_command(self, env, file_name, **flags):
        raise NotImplementedError

    def run(self, reason='unknown', compress=False, **flags):
        file_name = self.get_path(env, reason)
        command = self.get_command(env, file_name, **flags)
        run(command)
        if compress:
            run('gzip ' + file_name)
            file_name += '.gz'
        return file_name

    def get_flags_string(self, **flags):
        flag_list = []
        for k, v in flags.iteritems():
            result = ('-' if len(k) == 1 else '--') + k
            if v:
                result += (' ' if len(k) == 1 else '=') + v
            flag_list.append(result)
        return ' '.join(flag_list)


class DownloadDatabase(Task):
    """
    Download the database
    """

    name = 'download'

    def __init__(self, dump_task, **flags):
        self.dump_task = dump_task
        self.flags = flags

    def run(self, path='tmp', **flags):
        flags.update(self.flags)
        file_name = self.dump_task.run(reason='for_download', compress=True, **flags)
        get(file_name, path)
