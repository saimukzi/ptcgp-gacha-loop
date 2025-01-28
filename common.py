import const
import cv2
import my_logger
import numpy as np
import os
import time

def find_file(folder_path):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            yield os.path.join(root, file)

# opencv2 have problem with reading file from path with non-ascii character
def cv2_imread(file_path, flags=cv2.IMREAD_COLOR, *args, **kwargs):
    with open(file_path, 'rb') as f:
        bytess = f.read()
        return cv2.imdecode(np.frombuffer(bytess, np.uint8), flags=flags, *args, **kwargs)

def cv2_imwrite(file_path, img, params=None):
    retry_remain = 5
    while True:
        try:
            bytess = cv2.imencode('.png', img, params=params)[1].tobytes()
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(bytess)
            break
        except:
            retry_remain -= 1
            my_logger.logger.error(f'FGRISMSNBX Error in cv2_imwrite: {file_path}, retry_remain: {retry_remain}')
            if retry_remain <= 0:
                raise
            time.sleep(0.1)

def load_img_matcher(img_min_fn,img_max_fn,img_svmin_fn,img_svmax_fn,img_mask_fn, input_mask255f_img):
    img_min = cv2_imread(img_min_fn).astype(np.float32)
    img_max = cv2_imread(img_max_fn).astype(np.float32)

    if os.path.exists(img_svmin_fn):
        assert(os.path.exists(img_svmax_fn))
        img_svmin = cv2_imread(img_svmin_fn).astype(np.float32)
        img_svmin = img_svmin[:,:,0:2]
        img_svmax = cv2_imread(img_svmax_fn).astype(np.float32)
        img_svmax = img_svmax[:,:,0:2]
        img_min = np.append(img_min, img_svmin, axis=2)
        img_max = np.append(img_max, img_svmax, axis=2)

    if os.path.exists(img_mask_fn):
        img_mask = cv2_imread(img_mask_fn, flags=cv2.IMREAD_UNCHANGED).astype(np.float32)
        assert(img_mask.shape[2] == 4)
        img_mask = img_mask[:,:,3:4]
    else:
        img_mask = None

    if input_mask255f_img is not None:
        if img_mask is None:
            img_mask = input_mask255f_img
        else:
            img_mask = input_mask255f_img * img_mask / 255

    return {
        'img_min': img_min,
        'img_max': img_max,
        'img_mask': img_mask,
    }

def img_match(src_img, src_img_mask, state_data, debug=False):
    imgmx = src_img.max(axis=2)
    imgmn = src_img.min(axis=2)
    imgs = imgmx-imgmn
    imgv = imgmx
    imgsv = np.stack([imgs, imgv], axis=2)
    src_img = np.append(src_img, imgsv, axis=2)

    state_img_min = state_data['img_min']
    state_img_max = state_data['img_max']
    state_img_mask = state_data['img_mask']

    assert(state_img_min.shape == state_img_max.shape)
    if state_img_min.shape[2] == 3:
        src_img = src_img[:,:,:3]

    diff_max = src_img - state_img_max
    diff_max = np.maximum(diff_max, 0)
    diff_min = state_img_min - src_img
    diff_min = np.maximum(diff_min, 0)
    diff = np.maximum(diff_max, diff_min)

    if state_img_mask is not None:
        mask = state_img_mask
    else:
        mask = np.ones(src_img.shape[:2]+(1,), dtype=np.float32) * 255

    if src_img_mask is not None:
        # logger.debug('PPBJPURJGC src_mask_hwab is not None')
        mask = mask * src_img_mask
    # mask = mask.reshape(mask.shape[:2])
    mask = mask / 255
    diff = diff * mask

    if debug:
        fn = os.path.join(const.MY_PATH, 'debug', 'img_match', f'{int(time.time())}.diff.png')
        my_logger.logger.debug(f'img_match: {fn}')
        cv2_imwrite(fn, diff[:,:,:3].astype(np.uint8))
        fn = os.path.join(const.MY_PATH, 'debug', 'img_match', f'{int(time.time())}.mask.png')
        mask_hwc = np.zeros((mask.shape[0], mask.shape[1], 3), dtype=np.uint8)
        mask_hwc[:,:] = mask * 255
        cv2_imwrite(fn, mask_hwc.astype(np.uint8))

    mask_sum = mask.sum()
    diff = diff.sum() / mask_sum / src_img.shape[2]

    return diff

def OIZEASGTBP(txt):
    for d,c in enumerate('OIZEASGTBP'):
        txt = txt.replace(str(d),c)
    return txt
