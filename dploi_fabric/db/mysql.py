from fabric.tasks import Task
from dploi_fabric.db.base import DumpDatabaseTask, DownloadDatabase

class MysqlDumpDatabaseTask(DumpDatabaseTask, Task):
    """
    Dump the database (MySQL)
    """
    name = 'dump'

    def get_command(self, env, file_name, **flags):
        if hasattr(env, 'db_host'):
            flags['host'] = env['db_host']
        return ('mysqldump --user="%(db_username)s" --password="%(db_password)s" ' + self.get_flags_string(**flags) + ' "%(db_name)s" > ' % env) + file_name

dump = MysqlDumpDatabaseTask()
download = DownloadDatabase(dump_task=dump, l='') # l: lock tables
