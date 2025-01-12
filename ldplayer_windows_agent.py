import atexit
import os
import cv2
import my_path
import numpy as np
import pygetwindow as gw
import threading
import time

import common
import config
import const
from my_logger import logger
from windows_capture import WindowsCapture, Frame, InternalCaptureControl

TARGET_INNER_W = 300
TARGET_INNER_H = 400

# global
bar_color = None
bg_color = None
bareexist_to_target_outer_wh_dict = {}
bareexist_to_calibrate_data_dict = {}

class LDPlayerWindowsAgent:

    def __init__(self, window_name):
        self.window_name = window_name

        # windows size control
        all_windows = gw.getWindowsWithTitle(self.window_name)
        assert len(all_windows) == 1
        self.game_window = all_windows[0]

        # windows capture
        self.windows_capture = WindowsCapture(
            cursor_capture=False,
            draw_border=None,
            monitor_index=None,
            window_name=self.window_name,
        )
        self.windows_capture.frame_handler = self._windows_capture__frame_handler
        self.windows_capture.closed_handler = self._windows_capture__closed_handler
        self.windows_capture_control = None

        self.img_condition = threading.Condition()
        # self.img_tmp = None
        self.img_data_tmp = None
        self.img_idx = 0

        # self.last_img_bareexist = None
        self._require_calibrate = True
        

    def start(self):
        self.windows_capture_control = self.windows_capture.start_free_threaded()
        atexit.register(self._atexit)

    def stop(self):
        if self.windows_capture_control is not None:
            self.windows_capture_control.stop()
            self.windows_capture_control = None
            atexit.unregister(self._atexit)


    # def get_img_wh_m(self, auto_restore=True, nnext=False):
    #     with self.img_condition:
    #         old_img_idx = self.img_idx
    #         while True:
    #             if auto_restore:
    #                 self.restore_game_window_m()
    #             if nnext and (self.img_idx == old_img_idx):
    #                 self.img_condition.wait(0.1)
    #                 continue
    #             ret_img = self.img_tmp
    #             if ret_img is None:
    #                 self.img_condition.wait(0.1)
    #                 continue
    #             _detect_bar_color(ret_img)
    #             self.last_img_bareexist = get_bareexist(ret_img)
    #             img_wh = (ret_img.shape[1], ret_img.shape[0])
    #             if auto_restore:
    #                 if img_wh != self.game_window.size:
    #                     self.img_condition.wait(0.1)
    #                     continue
    #                 if self.last_img_bareexist not in bareexist_to_target_outer_wh_dict:
    #                     self._detect_target_outer_wh_m()
    #                     continue
    #                 if img_wh != bareexist_to_target_outer_wh_dict[self.last_img_bareexist]:
    #                     self.fix_target_wh_m()
    #                     continue
    #             # common.cv2_imwrite('get_img_wh_m.png', ret_img)
    #             return ret_img, img_wh

    def get_img_data(self, nnext=False):
        with self.img_condition:
            old_img_idx = self.img_idx
            while True:
                if nnext and (self.img_idx == old_img_idx):
                    self.img_condition.wait(0.1)
                    continue
                ret_img_data = self.img_data_tmp
                if ret_img_data is None:
                    self.img_condition.wait(0.1)
                    continue
                # _detect_bar_color(ret_img)
                # self.last_img_bareexist = get_bareexist(ret_img)
                img = ret_img_data['img']
                # img_wh = (ret_img.shape[1], ret_img.shape[0])
                ret_img_data['wh'] = (img.shape[1], img.shape[0])
                if config.my_config_data['DEBUG_MODE']:
                    common.cv2_imwrite(os.path.join(my_path.instance_debug(), 'get_img_data.png'), img)
                # return ret_img, img_wh
                return ret_img_data

    def get_calibrated_img_mask_m(self):
        logger.debug(f'PAQSBDIAQU get_calibrated_img_mask_m')
        self.restore_game_window_m()
        self.fix_target_wh_m()
        img_data = self.get_img_data()
        bareexist = get_bareexist(img_data)
        # img, wh = self.get_img_wh_m()
        # bareexist = get_bareexist(img)
        if bareexist not in bareexist_to_calibrate_data_dict:
            self._require_calibrate = True
            return None, None
        if bareexist not in bareexist_to_target_outer_wh_dict:
            return None, None
        target_outer_wh = bareexist_to_target_outer_wh_dict[bareexist]
        if img_data['wh'] != target_outer_wh:
            return None, None
        # calibrate_data = bareexist_to_calibrate_data_dict[bareexist]
        # img_data['calibrate_data'] = bareexist_to_calibrate_data_dict[bareexist]
        calibrate_img(img_data)
        return img_data['calibrate_img'], img_data['calibrate_mask']


    def calibrate_m(self, adb_img, mask_hwaf1):
        # img, wh = self.get_img_wh_m(nnext=True)
        self.restore_game_window_m()
        img_data = self.get_img_data(nnext=True)
        bareexist = get_bareexist(img_data)
        logger.debug(f'BACGWQPWBP bareexist={bareexist}')
        if bareexist in bareexist_to_calibrate_data_dict:
            logger.debug('LIZHDDQLTY already calibrated')
            self._require_calibrate = False
            return
        _detect_bar_color(img_data)
        self._detect_bg_color_m()
        self.fix_target_wh_m()
        
        self.restore_game_window_m()
        img_data = self.get_img_data(nnext=True)
        img = img_data['img']
        wh = img_data['wh']

        adb_bgr = adb_img[:,:,:3]

        h,w = img.shape[:2]

        img10 = np.equal(img, bar_color).all(axis=2)
        img11 = np.equal(img, bg_color).all(axis=2)
        img1 = np.logical_or(img10, img11)

        y_sum = img1.sum(axis=1)
        y_not_bar = (y_sum < w//4)
        y_not_bar[0] = False
        y_not_bar[-1] = False
        y_not_bar_nonzero = y_not_bar.nonzero()
        game_y0 = int(y_not_bar_nonzero[0][0])
        game_y1 = int(y_not_bar_nonzero[0][-1])+1

        x_sum = img1.sum(axis=0)
        x_not_bar = (x_sum < h//4)
        x_not_bar[0] = False
        x_not_bar[-1] = False
        x_not_bar_nonzero = x_not_bar.nonzero()
        game_x0 = int(x_not_bar_nonzero[0][0])
        game_x1 = int(x_not_bar_nonzero[0][-1])+1

        game_w = game_x1 - game_x0
        game_h = game_y1 - game_y0
        game_wh = (game_w, game_h)
        logger.debug(f'FTNVLLKQUI game_wh={game_wh}')

        src_mask9 = img[game_y0-1:game_y1+1, game_x0-1:game_x1+1, 3]

        src_mask9[0,:] = 0
        src_mask9[-1,:] = 0
        src_mask9[:,0] = 0
        src_mask9[:,-1] = 0
        src_mask9 = (src_mask9==255)

        mask = np.ones((game_h, game_w), np.bool)
        for i in range(3):
            for j in range(3):
                src_mask1 = src_mask9[i:game_h+i, j:game_w+j]
                mask = np.logical_and(mask, src_mask1)
        mask = mask.reshape(game_h, game_w, 1)

        best_ij = None
        best_diff = float('inf')

        screen_img = img[game_y0:game_y1, game_x0:game_x1, :3]

        for i in range(0, TARGET_INNER_H-game_h+1):
            for j in range(0, TARGET_INNER_W-game_w+1):
                adb_bgr_crop = adb_bgr[i:i+game_h, j:j+game_w]
                mask_hwaf1_crop = mask_hwaf1[i:i+game_h, j:j+game_w]
                diff = np.sum(np.abs(adb_bgr_crop - screen_img)*mask*mask_hwaf1_crop)
                if diff < best_diff:
                    best_diff = diff
                    best_ij = (i,j)

        logger.debug(f'HKHCVJTXVI best_diff={best_diff}, best_ij={best_ij}')
        best_i, best_j = best_ij

        target_mask_hwa = np.zeros((TARGET_INNER_H, TARGET_INNER_W, 1), np.bool)
        target_mask_hwa[best_i:best_i+game_h, best_j:best_j+game_w] = mask

        # target_mask_rgb = np.zeros((TARGET_INNER_H, TARGET_INNER_W, 3), np.uint8)
        # target_mask_rgb[:,:,:3] = target_mask_hwa * 255
        # common.cv2_imwrite('target_mask.png', target_mask_rgb)

        src_yyxx = game_y0, game_y1, game_x0, game_x1
        logger.debug(f'KQMXMROXWP bareexist:{bareexist} src_yyxx: {src_yyxx}')

        dest_yyxx = best_i, best_i+game_h, best_j, best_j+game_w
        logger.debug(f'RRGNMXMUWZ bareexist:{bareexist} dest_yyxx: {dest_yyxx}')

        calibrate_data = {
            'mask': target_mask_hwa,
            'src_yyxx': src_yyxx,
            'dest_yyxx': dest_yyxx,
        }
        bareexist_to_calibrate_data_dict[bareexist] = calibrate_data
        # logger.debug(f'XPAUNVZVIT bareexist_to_calibrate_data_dict: {bareexist_to_calibrate_data_dict}')

    def require_calibrate(self):
        # logger.debug(f'OFFABARANL require_calibrate last_img_bareexist: {self.last_img_bareexist}')
        # if self.last_img_bareexist is None:
        #     return True
        # return self.last_img_bareexist not in bareexist_to_calibrate_data_dict
        return self._require_calibrate

    def restore_game_window_m(self):
        good = False
        while not good:
            good = True
            if self.game_window.isMinimized:
                self.game_window.restore()
                good = False
            if self.game_window.isMaximized:
                self.game_window.restore()
                good = False
            if good:
                break
            time.sleep(0.1)

    # def get_mask_hwa(self):
    #     if self.last_img_bareexist is None:
    #         return None
    #     if self.last_img_bareexist not in bareexist_to_calibrate_data_dict:
    #         return None
    #     calibrate_data = bareexist_to_calibrate_data_dict[self.last_img_bareexist]
    #     return calibrate_data['mask']

    def fix_target_wh_m(self):
        self.restore_game_window_m()
        self._detect_target_outer_wh_m()
        img_data = self.get_img_data()
        bareexist = get_bareexist(img_data)
        self._change_wh_m(bareexist_to_target_outer_wh_dict[bareexist])

    def _detect_target_outer_wh_m(self):
        self.restore_game_window_m()
        img_data = self.get_img_data()
        bareexist = get_bareexist(img_data)
        if bareexist not in bareexist_to_target_outer_wh_dict:
            target_outer_wh = self.__detect_target_outer_wh_m()
            bareexist_to_target_outer_wh_dict[bareexist] = target_outer_wh

    def __detect_target_outer_wh_m(self):
        self.restore_game_window_m()
        self._detect_bg_color_m()
        # img, wh = self.get_img_wh_m()
        img_data = self.get_img_data()
        bar_n, bar_s, bar_w, bar_e = get_bar_nswe(img_data)
        logger.debug(f'NWKDLGNXQG bar_n={bar_n}, bar_e={bar_e}')

        # find target_outer_width
        le = TARGET_INNER_W - 20
        g = TARGET_INNER_W + bar_w + bar_e + 20

        while g-le > 1:
            m = (le+g)//2
            self._change_wh_m((m,TARGET_INNER_H + bar_n + bar_s + 20))
            img_data = self.get_img_data(nnext=True)
            img = img_data['img']
            # have saw case skipped value, need more frame to confirm
            for _ in range(5):
                img1 = np.equal(img, bg_color).all(axis=2)
            y_sum = img1.sum(axis=1)
            y_bg = (y_sum > m//4)
            x0 = m//2
            while (not y_bg[x0]):
                x0 -= 1
            x0 += 1
            x1 = m//2
            while (not y_bg[x1]):
                x1 += 1
            game_h = x1 - x0
            logger.debug(f'ZIXANFIVVU m={m}, game_h={game_h}')
            if game_h > TARGET_INNER_H:
                g = m
            else:
                le = m
        target_outer_width = le

        le = TARGET_INNER_H - 20
        g = TARGET_INNER_H + bar_n + bar_s + 20

        while g-le > 1:
            m = (le+g)//2
            self._change_wh_m((TARGET_INNER_W + bar_w + bar_e + 20,m))
            img_data = self.get_img_data(nnext=True)
            img = img_data['img']
            # have saw case skipped value, need more frame to confirm
            for _ in range(5):
                img1 = np.equal(img, bg_color).all(axis=2)
            x_sum = img1.sum(axis=0)
            x_bg = (x_sum > m//4)
            y0 = m//2
            while (not x_bg[y0]):
                y0 -= 1
            y0 += 1
            y1 = m//2
            while (not x_bg[y1]):
                y1 += 1
            game_w = y1 - y0
            logger.debug(f'SCLUPUARAX m={m} game_w={game_w}')
            if game_w > TARGET_INNER_W:
                g = m
            else:
                le = m
        
        target_outer_height = le

        return target_outer_width, target_outer_height

    def _detect_bg_color_m(self):
        if bg_color is not None:
            return
        self.restore_game_window_m()
        img_data = self.get_img_data()
        bar_n,bar_s,bar_w,bar_e = get_bar_nswe(img_data)
        self._change_wh_m((TARGET_INNER_W+40+bar_w+bar_e,TARGET_INNER_H+bar_n+bar_s))
        img_data = self.get_img_data(nnext=True)
        _detect_bg_color(img_data)

    def _change_wh_m(self, wh):
        while True:
            self.restore_game_window_m()
            self.game_window.size = wh
            img_data = self.get_img_data()
            if img_data['wh'] == wh:
                return

    def _atexit(self):
        if self.windows_capture_control is not None:
            self.windows_capture_control.stop()
            self.windows_capture_control = None

    def _windows_capture__frame_handler(self, frame: Frame, capture_control: InternalCaptureControl):
        #frame.save_as_img("tmp.png")
        with self.img_condition:
            self.img_data_tmp = {
                'img': frame.frame_buffer,
                'idx': self.img_idx,
            }
            self.img_idx += 1
            self.img_idx %= 1000000
            self.img_condition.notify()

    def _windows_capture__closed_handler(self):
        print("Capture Session Closed")
        if self.windows_capture_control is not None:
            self.windows_capture_control.stop()
            self.windows_capture_control = None
            atexit.unregister(self._atexit)


def calibrate_img(img_data):
    if 'calibrate_img' in img_data:
        return

    bareexist = get_bareexist(img_data)

    if bareexist not in bareexist_to_calibrate_data_dict:
        logger.debug(f'OVIIIDDDWJ calibrate_img bareexist={bareexist}')
        assert(False)

    calibrate_data = bareexist_to_calibrate_data_dict[bareexist]

    img = img_data['img']
    sy0, sy1, sx0, sx1 = calibrate_data['src_yyxx']
    dy0, dy1, dx0, dx1 = calibrate_data['dest_yyxx']

    ret_img = np.zeros((TARGET_INNER_H, TARGET_INNER_W, 3), np.uint8)
    ret_img[dy0:dy1, dx0:dx1] = img[sy0:sy1, sx0:sx1, :3]

    # common.cv2_imwrite('calibrate_img.png', ret_img)

    img_data['calibrate_img'] = ret_img
    img_data['calibrate_mask'] = calibrate_data['mask']

    return


def get_bareexist(img_data):
    if 'bareexist' in img_data:
        return img_data['bareexist']
    _,_,_,bar_e = get_bar_nswe(img_data)
    ret = bar_e > 4
    img_data['bareexist'] = ret
    return ret


def get_bar_nswe(img_data):
    if 'bar_nswe' in img_data:
        return img_data['bar_nswe']

    _detect_bar_color(img_data)

    img = img_data['img']

    img1 = np.equal(img, bar_color).all(axis=2)
    h,w = img1.shape

    y_sum = img1.sum(axis=1)
    y_not_bar = (y_sum < w//4)
    y_not_bar[0] = False
    y_not_bar[-1] = False
    y_not_bar_nonzero = y_not_bar.nonzero()
    bar_y0 = int(y_not_bar_nonzero[0][0])
    bar_y1 = int(y_not_bar_nonzero[0][-1])+1

    x_sum = img1.sum(axis=0)
    x_not_bar = (x_sum < h//4)
    x_not_bar[0] = False
    x_not_bar[-1] = False
    x_not_bar_nonzero = x_not_bar.nonzero()
    bar_x0 = int(x_not_bar_nonzero[0][0])
    bar_x1 = int(x_not_bar_nonzero[0][-1])+1
    
    bar_n = bar_y0
    bar_s = h-bar_y1
    bar_w = bar_x0
    bar_e = w-bar_x1

    ret = bar_n, bar_s, bar_w, bar_e
    img_data['bar_nswe'] = ret
    return ret

def _detect_bar_color(img_data):
    global bar_color
    if bar_color is not None:
        return
    img = img_data['img']
    if config.my_config_data['DEBUG_MODE']:
        common.cv2_imwrite(os.path.join(my_path.instance_debug(), 'bar_color.png'), img)
    bar_color = _top_count_color(img[1:3])
    logger.debug(f'KKZHHDZLRF bar_color: {bar_color}')

def _detect_bg_color(img_data):
    global bg_color
    if bg_color is not None:
        return
    img = img_data['img']
    if config.my_config_data['DEBUG_MODE']:
        common.cv2_imwrite(os.path.join(my_path.instance_debug(), 'bg_color.png'), img)
    bg_color = _top_count_color(img[:, 3:6])
    logger.debug(f'ETRRWXBHIS bg_color: {bg_color}')

def _top_count_color(img):
    img = img.reshape(-1, img.shape[2])
    color_list, count_list = np.unique(img, axis=0, return_counts=True)
    idx_max = count_list.argmax()
    return color_list[idx_max]


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--window_name", type=str)
    args = parser.parse_args()

    agent = LDPlayerWindowsAgent(args.window_name)
    agent.start()
    while True:
        img, wh = agent.get_img_wh_m()
        print(f'wh: {wh}')
        bar_nswe = get_bar_nswe(img)
        print(f'bar_nswe: {bar_nswe}')
        agent.fix_target_wh_m()
        time.sleep(0.5)

if __name__ == "__main__":
    main()
