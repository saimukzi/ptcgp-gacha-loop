import os
import sys

MY_PATH = os.path.dirname(os.path.abspath(__file__))

if getattr(sys, 'frozen', False):
    APP_PATH = os.path.dirname(sys.executable)
else:
    APP_PATH = MY_PATH

LOGGER_NAME = 'PTCGP_GACHA_LOOP'

TARGET_PACK_LIST = ['charizard', 'mewtwo', 'pikachu', 'mew']

VERSION_FN = os.path.join(MY_PATH, 'version.txt')
