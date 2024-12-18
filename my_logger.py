import logging
import const
import os
import time

logger = logging.getLogger(const.LOGGER_NAME)
logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG,
)

logger_file_handler = None
logger_file_handler_yyyymmddhh = None
def update_logger(config_data):
    global logger_file_handler, logger_file_handler_yyyymmddhh
    if not config_data['DEBUG_MODE']: return
    yyyymmddhh = time.strftime('%Y%m%d%H', time.localtime(time.time()))
    yyyy = yyyymmddhh[:4]
    mm = yyyymmddhh[4:6]
    dd = yyyymmddhh[6:8]
    hh = yyyymmddhh[8:10]
    if yyyymmddhh == logger_file_handler_yyyymmddhh:
        return
    if logger_file_handler is not None:
        logger.removeHandler(logger_file_handler)
        logger_file_handler = None
    fn = os.path.join('log', yyyy, mm, dd, f'{yyyy}{mm}{dd}-{hh}.log')
    # print(fn)
    os.makedirs(os.path.dirname(fn), exist_ok=True)
    logger_file_handler = logging.FileHandler(fn)
    logger_file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger_file_handler.setLevel(logging.DEBUG)
    logger.addHandler(logger_file_handler)
    logger_file_handler_yyyymmddhh = yyyymmddhh
