import os
import cv2

# LDPLAYER_PATH = r'D:\LDPlayer\LDPlayer9'
# EMU_INDEX = 0

LDPLAYER_PATH = None
LDCONSOLE_PATH = None
LD_EMU_NAME = 'LDPlayer'

def set_LD_EMU_NAME(name):
    global LD_EMU_NAME
    LD_EMU_NAME = name

def set_LDPLAYER_PATH(path):
    global LDPLAYER_PATH, LDCONSOLE_PATH
    LDPLAYER_PATH = path
    LDCONSOLE_PATH = os.path.join(LDPLAYER_PATH, 'ldconsole.exe')

def check():
    if not os.path.exists(LDPLAYER_PATH):
        print('Please set the correct LDPlayer path in ldagent.py')
        return False
    if not os.path.exists(LDCONSOLE_PATH):
        print('Please set the correct LDPlayer path in ldagent.py')
        return False
    return True

def screencap():
    os.system(f'{LDCONSOLE_PATH} adb --name {LD_EMU_NAME} --command "shell screencap -p /sdcard/tmp-screencap.png"')
    os.system(f'{LDCONSOLE_PATH} adb --name {LD_EMU_NAME} --command "pull /sdcard/tmp-screencap.png"')
    img = cv2.imread('tmp-screencap.png')
    return img

def tap(x, y):
    os.system(f'{LDCONSOLE_PATH} adb --name {LD_EMU_NAME} --command "shell input tap {x} {y}"')

def input_text(txt):
    os.system(f'{LDCONSOLE_PATH} action --name {LD_EMU_NAME} --key call.input --value {txt}')

def swipe(x1, y1, x2, y2, duration):
    os.system(f'{LDCONSOLE_PATH} adb --name {LD_EMU_NAME} --command "shell input swipe {x1} {y1} {x2} {y2} {duration}"')

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

if __name__ == '__main__':
    check()
    print('END')
