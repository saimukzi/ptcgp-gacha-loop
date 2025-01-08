import common
import os
import shutil
import time
import const
import cv2
import yaml
import ldagent
import argparse
import numpy as np
import config

def main():
    parser = argparse.ArgumentParser(description='Capture state')
    parser.add_argument('--append', action='store_true')
    parser.add_argument('config', type=str)
    parser.add_argument('state', type=str)
    parser.add_argument('sec', type=int, nargs='?')
    args = parser.parse_args()

    # config_data = yaml.load(open(args.config, 'r'), Loader=yaml.FullLoader)
    config_data = config.get_config(args.config)
    # ldagent.config(config_data)
    my_ldagent = ldagent.get_ldagent(config_data)

    img_min = None
    img_max = None
    img_svmin = None
    img_svmax = None

    img_min_fn = os.path.join(const.MY_PATH, 'res', 'state', f'{args.state}.min.png')
    img_max_fn = os.path.join(const.MY_PATH, 'res', 'state', f'{args.state}.max.png')
    img_svmin_fn = os.path.join(const.MY_PATH, 'res', 'state', f'{args.state}.svmin.png')
    img_svmax_fn = os.path.join(const.MY_PATH, 'res', 'state', f'{args.state}.svmax.png')

    if not args.append:
        if os.path.exists(img_min_fn):
            raise('File already exists')
        if os.path.exists(img_max_fn):
            raise('File already exists')
        if os.path.exists(img_svmin_fn):
            raise('File already exists')
        if os.path.exists(img_svmax_fn):
            raise('File already exists')
    else:
        if os.path.exists(img_min_fn):
            shutil.copyfile(img_min_fn, img_min_fn + '.bak')
            img_min = common.cv2_imread(img_min_fn)
        if os.path.exists(img_max_fn):
            shutil.copyfile(img_max_fn, img_max_fn + '.bak')
            img_max = common.cv2_imread(img_max_fn)
        if os.path.exists(img_svmin_fn):
            shutil.copyfile(img_svmin_fn, img_svmin_fn + '.bak')
            img_svmin = common.cv2_imread(img_svmin_fn)
        if os.path.exists(img_svmax_fn):
            shutil.copyfile(img_svmax_fn, img_svmax_fn + '.bak')
            img_svmax = common.cv2_imread(img_svmax_fn)

    t = time.time()
    i = 0
    while True:
        img = my_ldagent.adb_screencap()
        img_zmax = img.max(axis=2)
        img_zmin = img.min(axis=2)
        imgs = (img_zmax - img_zmin).astype(img.dtype)
        imgv = img_zmax.astype(img.dtype)
        imgz = np.zeros_like(img_zmax, dtype=img.dtype)
        imgsv = np.stack([imgs, imgv, imgz], axis=2).astype(img.dtype)
        img_min = cv2_min(img_min, img)
        img_max = cv2_max(img_max, img)
        img_svmin = cv2_min(img_svmin, imgsv)
        img_svmax = cv2_max(img_svmax, imgsv)
        i += 1
        if args.sec is None and i >= 100:
            break
        if args.sec is not None and time.time() - t >= args.sec:
            break
        time.sleep(0.05)
    
    os.makedirs(os.path.join(const.MY_PATH, 'res', 'state'), exist_ok=True)

    cv2.imwrite(img_max_fn, img_max)
    cv2.imwrite(img_min_fn, img_min)
    cv2.imwrite(img_svmax_fn, img_svmax)
    cv2.imwrite(img_svmin_fn, img_svmin)

def cv2_min(i0, i1):
    if i0 is None:
        return i1
    if i1 is None:
        return i0
    return cv2.min(i0, i1)

def cv2_max(i0, i1):
    if i0 is None:
        return i1
    if i1 is None:
        return i0
    return cv2.max(i0, i1)

if __name__ == '__main__':
    main()
