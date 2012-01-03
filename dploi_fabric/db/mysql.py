from fabric.tasks import Task
from dploi_fabric.db.base import DumpDatabaseTask, DownloadDatabase

class MysqlDumpDatabaseTask(DumpDatabaseTask, Task):
    """
    Dump the database (MySQL)
    """
    name = 'dump'

    def run(self, reason='unknown', compress=False, nolock=False):
        self.nolock = nolock
        return super(MysqlDumpDatabaseTask, self).run(reason, compress)

    def get_command(self, env, file_name):
        nolock = ' --lock-tables=false' if self.nolock else ''
        host = ' --host %(db_host)s' % env if hasattr(env, 'db_host') else ''
        return ('mysqldump' + nolock + host + ' --user="%(db_username)s" --password="%(db_password)s" "%(db_name)s" > ' % env) + file_name

dump = MysqlDumpDatabaseTask()
download = DownloadDatabase(dump_task=dump)
