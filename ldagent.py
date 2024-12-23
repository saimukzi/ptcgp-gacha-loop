import os
import shutil
import time
import cv2
import subprocess
from my_logger import logger
import charset_normalizer
import const
import json

# LDPLAYER_PATH = r'D:\LDPlayer\LDPlayer9'
# EMU_INDEX = 0

PACKAGE_NAME = 'jp.pokemon.pokemontcgp'

INSTANCE_ID = None

LDPLAYER_PATH = None
LDCONSOLE_PATH = None
ADB_PATH = None

LD_EMU_NAME = 'LDPlayer'
EMU_IDX = None
ADB_IDX = None

SCREENCAP_PATH = None

def config(config_data):
    # set_LDPLAYER_PATH(config_data['LDPLAYER_PATH'])
    # set_LD_EMU_NAME(config_data['LD_EMU_NAME'])

    global INSTANCE_ID, LDPLAYER_PATH, LDCONSOLE_PATH, ADB_PATH, LD_EMU_NAME, EMU_IDX, ADB_IDX, SCREENCAP_PATH

    INSTANCE_ID = config_data['INSTANCE_ID']
    logger.debug(f'INSTANCE_ID = {INSTANCE_ID}')

    LDPLAYER_PATH = config_data['LDPLAYER_PATH']
    LDCONSOLE_PATH = os.path.join(LDPLAYER_PATH, 'ldconsole.exe')
    ADB_PATH = os.path.join(LDPLAYER_PATH, 'adb.exe')

    # checking
    if not os.path.exists(LDPLAYER_PATH):
        logger.error('QREGRQLDNY config LDPLAYER_PATH error')
        assert(False)        
    if not os.path.exists(LDCONSOLE_PATH):
        logger.error('IIFSOVLEDY ldconsole.exe not found')
        assert(False)        
    if not os.path.exists(ADB_PATH):
        logger.error('SNULPZOYCO adb.exe not found')
        assert(False)        
    
    LD_EMU_NAME = config_data['LD_EMU_NAME']
    logger.debug(f'AFCTNYVSXS LD_EMU_NAME = {LD_EMU_NAME}')
    process_ret = subprocess.run([LDCONSOLE_PATH, "list2"], capture_output=True, timeout=30)
    logger.debug(f'LFAYVDBGMH ldconsole list2 returncode = {process_ret.returncode}')
    assert(process_ret.returncode == 0)
    logger.debug(f'LWSKFFCJQD ldconsole list2 stdout = {process_ret.stdout}')

    pout = decode_console(process_ret.stdout).split('\r\n')
    # print(pout)
    EMU_IDX = None
    for line in pout:
        if len(line) <= 0: continue
        linee = line.split(',')
        if linee[1] != LD_EMU_NAME: continue
        EMU_IDX = linee[0]
        break
    logger.debug(f'WOBQVCANIM EMU_IDX = {EMU_IDX}')
    if EMU_IDX is None:
        logger.error('ZCLTJRWBVX config LD_EMU_NAME error')
        assert(False)
    
    # refer to https://help.ldmnq.com/docs/LD9adbserver
    ADB_IDX = str(int(EMU_IDX)*2+5554)
    logger.debug(f'LCBJLLYUJK ADB_IDX = {ADB_IDX}')

    # process_ret = subprocess.run([ADB_PATH, "-s", f"emulator-{ADB_IDX}", "shell", "echo", "ODSLKYUGNV"], capture_output=True, timeout=1)
    process_ret = subprocess.run([ADB_PATH, "version"], capture_output=True, timeout=10)
    logger.debug(f'VYCXJPKXSJ ADB version returncode = {process_ret.returncode}')
    assert(process_ret.returncode == 0) 
    logger.debug(f'GQINGWZXKN ADB version = {process_ret.stdout}')
    # pout = process_ret.stdout
    # pout = pout.decode('utf-8')
    # pout = pout.strip()
    # assert(pout == 'ODSLKYUGNV')

    SCREENCAP_PATH = os.path.join(const.APP_PATH, 'var', 'instances', INSTANCE_ID, 'tmp-screencap.png')

def screencap():
    adb_exec(['shell', 'screencap', '-p', '/sdcard/tmp-screencap.png'])
    adb_exec(['pull', '/sdcard/tmp-screencap.png', SCREENCAP_PATH])
    img = cv2.imread(SCREENCAP_PATH)
    return img

def tap(x, y):
    # os.system(f'{ADB_PATH} -s emulator-{ADB_IDX} shell input tap {x} {y}')
    adb_exec(['shell', 'input', 'tap', str(x), str(y)])

def input_text(txt):
    # os.system(f'{ADB_PATH} -s emulator-{ADB_IDX} shell input text "{txt}"')
    adb_exec(['shell', 'input', 'text', txt])

def swipe(x1, y1, x2, y2, duration):
    # os.system(f'{ADB_PATH} -s emulator-{ADB_IDX} shell input swipe {x1} {y1} {x2} {y2} {duration}')
    adb_exec(['shell', 'input', 'swipe', str(x1), str(y1), str(x2), str(y2), str(duration)])

def keyevent(key):
    # os.system(f'{ADB_PATH} -s emulator-{ADB_IDX} shell input keyevent {key}')
    adb_exec(['shell', 'input', 'keyevent', str(key)])

def recover():
    logger.debug('YTQEMXRINZ recover START')

    try:
        # check if emulator is running
        is_running = ldconsole_exec(['isrunning']).strip()
        is_running = (is_running == 'running')
        logger.debug(f'VBSBGEWIOX isrunning = {is_running}')

        force_kill = False

        # if bad screen size, force quit
        process_ret = subprocess.run([LDCONSOLE_PATH, 'list2'], capture_output=True, timeout=30)
        logger.debug(f'NPGOIQWVWC list2 returncode = {process_ret.returncode}')
        assert(process_ret.returncode == 0)
        logger.debug(f'LWSKFFCJQD list2 stdout = {process_ret.stdout}')
        list2_out = decode_console(process_ret.stdout).split('\r\n')
        for line in list2_out:
            if len(line) <= 0: continue
            linee = line.split(',')
            if linee[0] != EMU_IDX: continue
            if linee[7] != '300' or linee[8] != '400' or linee[9] != '120':
                force_kill = True
                break

        # check adb enabled
        emu_config_data_rewrite = False
        emu_config_path = os.path.join(LDPLAYER_PATH, 'vms', 'config', f'leidian{EMU_IDX}.config')
        assert(os.path.exists(emu_config_path))
        emu_config_data = json.load(open(emu_config_path, 'r'))
        assert(emu_config_data['statusSettings.playerName']==LD_EMU_NAME)
        if emu_config_data['basicSettings.adbDebug'] == 0:
            logger.debug(f'GANSNXERZV adbDebug is not enabled')
            emu_config_data['basicSettings.adbDebug'] = 1
            emu_config_data_rewrite = True
            force_kill = True

        # force kill
        if force_kill:
            logger.debug(f'UHMMGPTQTH force kill')
            killemu()

        # force screen size
        process_ret = subprocess.run([LDCONSOLE_PATH, "modify", '--index', str(EMU_IDX), "--resolution", "300,400,120"], capture_output=True, timeout=30)
        logger.debug(f'VNQSKTTRFC modify returncode = {process_ret.returncode}')
        assert(process_ret.returncode == 0)

        # update adb enabled
        if emu_config_data_rewrite:
            logger.debug(f'SRDWQJYJIR rewrite emu_config_data to {emu_config_path}')
            shutil.copyfile(emu_config_path, emu_config_path+'.bak')
            json.dump(emu_config_data, open(emu_config_path, 'w'), indent=4)

        # launch emu with app
        while True:
            process_ret = subprocess.run([LDCONSOLE_PATH, "isrunning", '--index', str(EMU_IDX)], capture_output=True, timeout=30)
            logger.debug(f'VNQSKTTRFC isrunning returncode = {process_ret.returncode}')
            assert(process_ret.returncode == 0)
            process_stdout = process_ret.stdout.decode('utf-8').strip()
            logger.debug(f'ZSQKAYSNNX isrunning stdout = {process_stdout}')
            if process_stdout == 'running':
                break
            elif process_stdout == 'stop':
                process_ret = subprocess.run([LDCONSOLE_PATH, 'launchex', '--index', str(EMU_IDX), '--packagename', PACKAGE_NAME], capture_output=True, timeout=30)
                logger.debug(f'PMHUALUBNQ launch returncode = {process_ret.returncode}')
                assert(process_ret.returncode == 0)
                # logger.debug(process_ret.stdout)
                # logger.debug(process_ret.stderr)
                time.sleep(5)
            else:
                logger.error(f'KRLUSFIKDV unknown ldconsole isrunning state: {process_stdout}')
                assert(False)

        while True:
            process_ret = subprocess.run([ADB_PATH, "-s", f"emulator-{ADB_IDX}",'shell', 'pidof', PACKAGE_NAME], capture_output=True, timeout=10)
            logger.debug(f'OIADLYZHXI pidof returncode = {process_ret.returncode}')
            if process_ret.returncode == 0:
                break
            process_ret = subprocess.run([LDCONSOLE_PATH, "runapp", '--index', str(EMU_IDX), '--packagename', PACKAGE_NAME], capture_output=True, timeout=30)
            logger.debug(f'OLEATIUZMY runapp returncode = {process_ret.returncode}')
            assert(process_ret.returncode == 0)
            time.sleep(5)
    except subprocess.TimeoutExpired:
        logger.error(f'CRSVCSYWPX recover timeout')
        raise LdAgentException('recover timeout')

def killemu():
    while True:
        process_ret = subprocess.run([LDCONSOLE_PATH, "isrunning", '--index', str(EMU_IDX)], capture_output=True, timeout=30)
        logger.debug(f'VNQSKTTRFC isrunning returncode = {process_ret.returncode}')
        assert(process_ret.returncode == 0)
        # process_stdout = process_ret.stdout.decode('utf-8').strip()
        process_stdout = decode_console(process_ret.stdout).strip()
        logger.debug(f'ZSQKAYSNNX isrunning stdout = {process_stdout}')
        if process_stdout == 'stop':
            break
        elif process_stdout == 'running':
            process_ret = subprocess.run([LDCONSOLE_PATH, 'quit', '--index', str(EMU_IDX)], capture_output=True, timeout=30)
            logger.debug(f'PMHUALUBNQ quit returncode = {process_ret.returncode}')
            assert(process_ret.returncode == 0)
            time.sleep(5)
        else:
            logger.error(f'KRLUSFIKDV unknown ldconsole isrunning state: {process_stdout}')
            assert(False)


def copyemu(new_name):
    logger.debug(f'ASCYGHOHGH copyemu START new_name = {new_name}')

    # check if new_name already exists
    list2_ret = ldconsole_list2()
    list2_ret = list(filter(lambda x: x['NAME']==new_name, list2_ret))
    logger.debug(f'ICYZPBNKEQ list2_ret = {list2_ret}')
    assert(len(list2_ret) == 0)

    # copy emu
    process_ret = subprocess.run([LDCONSOLE_PATH, "copy", '--name', new_name, '--from', str(EMU_IDX)], capture_output=True, timeout=30)
    logger.debug(f'VJZYCSTPMO copy returncode = {process_ret.returncode}')
    # assert(process_ret.returncode == 0)

    # check if new_name already exists
    list2_ret = ldconsole_list2()
    list2_ret = list(filter(lambda x: x['NAME']==new_name, list2_ret))
    logger.debug(f'PXSQPZBCVP list2_ret = {list2_ret}')
    assert(len(list2_ret) == 0)

def killapp():
    process_ret = subprocess.run([LDCONSOLE_PATH, "killapp", '--index', str(EMU_IDX), '--packagename', PACKAGE_NAME], capture_output=True, timeout=30)
    logger.debug(f'BRYURULFDU killapp returncode = {process_ret.returncode}')
    assert(process_ret.returncode == 0)


def reset():
    adb_exec(['shell', 'pm', 'clear', PACKAGE_NAME], timeout=30)

def is_emu_running():
    ret = ldconsole_exec(['isrunning']).strip()
    assert(ret in ['running', 'stop'])
    ret = (ret == 'running')
    logger.debug(f'QTNGYOPNKY isrunning = {ret}')
    return ret

def ldconsole_list2():
    logger.debug(f'JOASNOUJVA list2 START')
    process_ret = subprocess.run([LDCONSOLE_PATH, "list2"], capture_output=True, timeout=30)
    logger.debug(f'MFWLYOHPSZ list2 returncode = {process_ret.returncode}')
    assert(process_ret.returncode == 0)
    process_stdout = decode_console(process_ret.stdout)
    logger.debug(f'XYFXCQTLYX list2 stdout = {process_stdout}')
    # return process_stdout
    process_stdout = process_stdout.split('\r\n')
    ret = []
    for line in process_stdout:
        line = line.strip()
        if len(line) <= 0: continue
        line = line.split(',')
        ret.append({
            'IDX': line[0],
            'NAME': line[1],
            'WIDTH': line[7],
            'HEIGHT': line[8],
            'DPI': line[9],
        })
    return ret


# ldconsole backup is not working, fk it
# def backup(path):
#     process_ret = subprocess.run([LDCONSOLE_PATH, "backup", '--index', str(EMU_IDX), '--file', path], capture_output=True, timeout=120)
#     logger.debug(f'WNEGIMQAYH backup returncode = {process_ret.returncode}')
#     assert(process_ret.returncode == 0)
#
#
# def restore(path):
#     process_ret = subprocess.run([LDCONSOLE_PATH, "restore", '--index', str(EMU_IDX), '--file', path], capture_output=True, timeout=120)
#     logger.debug(f'WVOLRLKHAF restore returncode = {process_ret.returncode}')
#     assert(process_ret.returncode == 0)


def get_app_version():
    process_ret = subprocess.run([ADB_PATH, "-s", f"emulator-{ADB_IDX}", 'shell', 'dumpsys', 'package', PACKAGE_NAME], capture_output=True, timeout=10)
    logger.debug(f'CNIJYUXHFK dumpsys returncode = {process_ret.returncode}')
    assert(process_ret.returncode == 0)
    # process_stdout = process_ret.stdout.decode('utf-8')
    process_stdout = decode_console(process_ret.stdout)
    # print(process_stdout)
    for line in process_stdout.split('\n'):
        if 'versionName=' in line:
            return line.strip().split('=')[1].strip()
    assert(False)


def adb_exec(cmd, timeout=5):
    try:
        process_ret = subprocess.run([ADB_PATH, "-s", f"emulator-{ADB_IDX}"]+cmd, capture_output=True, timeout=timeout)
        if process_ret.returncode != 0:
            logger.error(f'RZBQUXKBHP adb_exec returncode = {process_ret.returncode}')
            raise LdAgentException('adb_exec returncode!=0')
    except subprocess.TimeoutExpired:
        logger.error(f'SZLGCPJJAD adb_exec timeout')
        raise LdAgentException('adb_exec timeout')

# cap_idx = 0
# def cap():
#     global cap_idx
#     img = screencap()
#     while True:
#         if not os.path.exists('cap/cap_{:04d}.png'.format(cap_idx)):
#             break
#         cap_idx += 1
#     cv2.imwrite('cap/cap_{:04d}.png'.format(cap_idx), img)
#     cap_idx += 1

def decode_console(bb):
    ret = charset_normalizer.from_bytes(bb).best().output().decode('utf-8')
    # print(ret)
    return ret

def ldconsole_exec(cmd, timeout=30):
    process_ret = subprocess.run([LDCONSOLE_PATH, cmd[0], '--index', str(EMU_IDX)]+cmd[1:], capture_output=True, timeout=timeout)
    logger.debug(f'NYUTUZCBMC isrunning returncode = {process_ret.returncode}')
    assert(process_ret.returncode == 0)
    process_stdout = decode_console(process_ret.stdout).strip()
    logger.debug(f'ADUVHMHEZL isrunning stdout = {process_stdout}')
    return process_stdout

class LdAgentException(Exception):
    pass

if __name__ == '__main__':
    import argparse
    import config as cconfig
    parser = argparse.ArgumentParser(description='LDPlayer Agent')
    parser.add_argument('config', type=str)
    args = parser.parse_args()

    config_data = cconfig.get_config(args.config)
    config(config_data)

    print('END')
