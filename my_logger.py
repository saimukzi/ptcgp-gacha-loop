import const
import logging
import os
import sys
import time

MY_PATH = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger(const.LOGGER_NAME)
logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG,
)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("WCEUIDZYXD Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

logger_file_handler = None
logger_file_handler_yyyymmddhh = None
def update_logger(config_data):
    global logger_file_handler, logger_file_handler_yyyymmddhh
    if not config_data['DEBUG_MODE']: return
    INSTANCE_ID = config_data['INSTANCE_ID']
    yyyymmddhh = time.strftime('%Y%m%d%H', time.localtime(time.time()))
    yyyy = yyyymmddhh[:4]
    mm = yyyymmddhh[4:6]
    dd = yyyymmddhh[6:8]
    hh = yyyymmddhh[8:10]
    if yyyymmddhh == logger_file_handler_yyyymmddhh:
        return
    fn = os.path.join(const.APP_PATH,'log','instances',INSTANCE_ID, yyyy, mm, dd, f'{yyyy}{mm}{dd}-{hh}.log')
    # print(fn)
    os.makedirs(os.path.dirname(fn), exist_ok=True)
    new_logger_file_handler = logging.FileHandler(fn, encoding='utf-8')
    new_logger_file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    new_logger_file_handler.setLevel(logging.DEBUG)
    logger.addHandler(new_logger_file_handler)
    if logger_file_handler is not None:
        logger.removeHandler(logger_file_handler)
        logger_file_handler = None
    logger_file_handler = new_logger_file_handler
    logger_file_handler_yyyymmddhh = yyyymmddhh
