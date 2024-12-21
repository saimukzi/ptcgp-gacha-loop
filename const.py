import os
import sys

MY_PATH = os.path.dirname(os.path.abspath(__file__))

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    APP_PATH = sys._MEIPASS
else:
    APP_PATH = MY_PATH

LOGGER_NAME = 'PTCGP_GACHA_LOOP'

TARGET_PACK_LIST = ['charizard', 'mewtwo', 'pikachu', 'mew']
