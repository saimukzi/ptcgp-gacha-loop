import argparse
import common
import config
import ldagent
import numpy as np
import os
import time

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=str)
    parser.add_argument('path', type=str)
    parser.add_argument('count', type=int)
    args = parser.parse_args()

    config_data = config.get_config(args.config)
    my_ldagent = ldagent.get_ldagent(config_data)
    
    for i in range(args.count):
        t = int(time.time())
        img = my_ldagent.adb_screencap()
        common.cv2_imwrite(os.path.join(args.path, f'{t}.png'), img)
        time.sleep(1.01)


if __name__ == '__main__':
    main()
