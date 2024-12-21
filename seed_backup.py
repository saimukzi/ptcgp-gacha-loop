import const
import ldagent
import os
import shutil

from my_logger import logger

class SeedBackup:
    def __init__(self, config_data):
        self.config_data = config_data
        self.__app_ver = None
        self.__folder_path = None
        self.__file_path = None

    def is_backup_available(self):
        ret = os.path.exists(self._get_file_path())
        logger.debug(f'NFKIOGCSMS is_backup_available: {ret}')
        return ret

    def backup(self):
        logger.debug('NYUTUZCBMC backup')
        shutil.rmtree(self._get_folder_path(), ignore_errors=True)
        os.makedirs(self._get_folder_path(), exist_ok=True)
        ldagent.backup(self._get_file_path())

    def restore(self):
        logger.debug('ADUVHMHEZL restore')
        assert(self.is_backup_available())
        ldagent.restore(self._get_file_path())

    def _get_folder_path(self):
        if self.__folder_path == None:
            self.__folder_path = os.path.join(const.APP_PATH, 'var', 'backup')
        return self.__folder_path

    def _get_file_path(self):
        if self.__file_path == None:
            app_ver = self._get_app_ver()
            self.__file_path = os.path.join(self._get_folder_path(), f'seed_backup_{app_ver}.ldbk')
        return self.__file_path

    def _get_app_ver(self):
        if self.__app_ver == None:
            self.__app_ver = ldagent.get_app_version()
        return self.__app_ver
