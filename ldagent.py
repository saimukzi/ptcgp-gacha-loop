import os
import cv2
import subprocess
from my_logger import logger

# LDPLAYER_PATH = r'D:\LDPlayer\LDPlayer9'
# EMU_INDEX = 0

LDPLAYER_PATH = None
LDCONSOLE_PATH = None
ADB_PATH = None

LD_EMU_NAME = 'LDPlayer'
ADB_IDX = None

def set_LDPLAYER_PATH(path):
    global LDPLAYER_PATH, LDCONSOLE_PATH, ADB_PATH
    LDPLAYER_PATH = path
    LDCONSOLE_PATH = os.path.join(LDPLAYER_PATH, 'ldconsole.exe')
    ADB_PATH = os.path.join(LDPLAYER_PATH, 'adb.exe')
    check()

def set_LD_EMU_NAME(name):
    global LD_EMU_NAME, ADB_IDX
    check()
    
    LD_EMU_NAME = name
    process_ret = subprocess.run([LDCONSOLE_PATH, "list2"], capture_output=True)

    pout = process_ret.stdout
    pout = pout.decode('utf-8')
    pout = pout.split('\r\n')

    emu_idx = None
    for line in pout:
        if len(line) <= 0: continue
        linee = line.split(',')
        if linee[1] != name: continue
        emu_idx = linee[0]
        break
    assert(emu_idx is not None)
    
    # refer to https://help.ldmnq.com/docs/LD9adbserver
    ADB_IDX = str(int(emu_idx)*2+5554)
    

def check():
    if not os.path.exists(LDPLAYER_PATH):
        logger.error('Please set the correct LDPlayer path in ldagent.py')
        return False
    if not os.path.exists(LDCONSOLE_PATH):
        logger.error('Please set the correct LDPlayer path in ldagent.py')
        return False
    if not os.path.exists(ADB_PATH):
        logger.error('Please set the correct LDPlayer path in ldagent.py')
        return False
    return True

def screencap():
    os.system(f'{ADB_PATH} -s emulator-{ADB_IDX} shell screencap -p /sdcard/tmp-screencap.png')
    os.system(f'{ADB_PATH} -s emulator-{ADB_IDX} pull /sdcard/tmp-screencap.png')
    img = cv2.imread('tmp-screencap.png')
    return img

def tap(x, y):
    os.system(f'{ADB_PATH} -s emulator-{ADB_IDX} shell input tap {x} {y}')

def input_text(txt):
    os.system(f'{ADB_PATH} -s emulator-{ADB_IDX} shell input text "{txt}"')

def swipe(x1, y1, x2, y2, duration):
    os.system(f'{ADB_PATH} -s emulator-{ADB_IDX} shell input swipe {x1} {y1} {x2} {y2} {duration}')

def keyevent(key):
    os.system(f'{ADB_PATH} -s emulator-{ADB_IDX} shell input keyevent {key}')

cap_idx = 0

def cap():
    global cap_idx
    img = screencap()
    while True:
        if not os.path.exists('cap/cap_{:04d}.png'.format(cap_idx)):
            break
        cap_idx += 1
    cv2.imwrite('cap/cap_{:04d}.png'.format(cap_idx), img)
    cap_idx += 1

def config(config_data):
    set_LDPLAYER_PATH(config_data['LDPLAYER_PATH'])
    set_LD_EMU_NAME(config_data['LD_EMU_NAME'])

if __name__ == '__main__':
    check()
    print('END')
