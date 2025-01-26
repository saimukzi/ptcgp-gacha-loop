import argparse
import common
import concurrent.futures as cf
import const
import cv2
import numpy as np
import os
import state_list
# import threading

def main():
    parser = argparse.ArgumentParser(description='Test state_list')
    # parser.add_argument('--state', help='state name', nargs='?', default=None)
    args = parser.parse_args()

    S11_HOURGLASS_00_NOHAND = common.load_img_matcher(
        os.path.join(const.MY_PATH, 'res', 's11-hourglass-00', 'nohand.min.png'),
        os.path.join(const.MY_PATH, 'res', 's11-hourglass-00', 'nohand.max.png'),
        os.path.join(const.MY_PATH, 'res', 's11-hourglass-00', 'nohand.svmin.png'),
        os.path.join(const.MY_PATH, 'res', 's11-hourglass-00', 'nohand.svmax.png'),
        os.path.join(const.MY_PATH, 'res', 's11-hourglass-00', 'nohand.mask.png'),
        None,
    )

    def process_fn(img_fn, pos):
        img = common.cv2_imread(img_fn, flags=cv2.IMREAD_UNCHANGED).astype(np.float32)
        mask = None
        if img.shape[2] == 4:
            mask = img[:,:,3:4]
            img = img[:,:,0:3]
        match_score = common.img_match(img, mask, S11_HOURGLASS_00_NOHAND)
        print(f'{img_fn} -> {match_score}')
        if pos:
            assert(match_score<1)
        else:
            assert(match_score>1)

    executor = cf.ThreadPoolExecutor()

    # testcases\s11-hourglass-00-nohand
    imgs_path = os.path.join(const.MY_PATH, 'testcases', 's11-hourglass-00-nohand','pos')

    fn_list = []
    for fn in os.listdir(imgs_path):
        if not fn.endswith('.png'):
            continue
        img_fn = os.path.join(imgs_path, fn)
        fn_list.append(img_fn)
    
    ret_itr = executor.map(lambda i:process_fn(i,True), fn_list)
    for ret in ret_itr:
        pass

    imgs_path = os.path.join(const.MY_PATH, 'testcases', 's11-hourglass-00-nohand','neg')

    fn_list = []
    for fn in os.listdir(imgs_path):
        if not fn.endswith('.png'):
            continue
        img_fn = os.path.join(imgs_path, fn)
        fn_list.append(img_fn)
    
    ret_itr = executor.map(lambda i:process_fn(i,False), fn_list)
    for ret in ret_itr:
        pass

if __name__ == '__main__':
    main()
