import os
import shutil
import time

import cv2
import ldagent
import argparse

def main():
    parser = argparse.ArgumentParser(description='Capture state')
    parser.add_argument('--append', action='store_true')
    parser.add_argument('state', type=str)
    args = parser.parse_args()
    
    img_min = None
    img_max = None

    img_min_fn = os.path.join('res', 'state', f'{args.state}.min.png')
    img_max_fn = os.path.join('res', 'state', f'{args.state}.max.png')

    if not args.append:
        if os.path.exists(img_min_fn):
            raise('File already exists')
        if os.path.exists(img_max_fn):
            raise('File already exists')
    else:
        shutil.copyfile(img_min_fn, img_min_fn + '.bak')
        shutil.copyfile(img_max_fn, img_max_fn + '.bak')
        img_min = cv2.imread(img_min_fn)
        img_max = cv2.imread(img_max_fn)


    for _ in range(100):
        img = ldagent.screencap()
        if img_min is None:
            img_min = img
            img_max = img
        else:
            img_min = cv2.min(img_min, img)
            img_max = cv2.max(img_max, img)
        time.sleep(0.05)
    
    os.makedirs(os.path.join('res', 'state'), exist_ok=True)

    cv2.imwrite(img_max_fn, img_max)
    cv2.imwrite(img_min_fn, img_min)

if __name__ == '__main__':
    main()
