import atexit
import cv2
import numpy as np
import pygetwindow as gw
import threading
import time

import common
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
            draw_border=True,
            monitor_index=None,
            window_name=self.window_name,
        )
        self.windows_capture.frame_handler = self._windows_capture__frame_handler
        self.windows_capture.closed_handler = self._windows_capture__closed_handler
        self.windows_capture_control = None

        self.img_condition = threading.Condition()
        self.img_tmp = None

        self.last_img_bareexist = None

    def start(self):
        self.windows_capture_control = self.windows_capture.start_free_threaded()
        atexit.register(self._atexit)

    def stop(self):
        if self.windows_capture_control is not None:
            self.windows_capture_control.stop()
            self.windows_capture_control = None
            atexit.unregister(self._atexit)


    def get_img_wh_m(self, auto_restore=True):
        with self.img_condition:
            while True:
                if auto_restore:
                    self.restore_game_window_m()
                ret_img = self.img_tmp
                if ret_img is None:
                    self.img_condition.wait(0.1)
                    continue
                _detect_bar_color(ret_img)
                self.last_img_bareexist = get_bareexist(ret_img)
                img_wh = (ret_img.shape[1], ret_img.shape[0])
                if img_wh == self.game_window.size:
                    return ret_img, img_wh
                self.img_condition.wait(0.1)


    def get_calibrated_img_mask_m(self):
        logger.debug(f'PAQSBDIAQU get_calibrated_img_m')
        img, wh = self.get_img_wh_m()
        bareexist = get_bareexist(img)
        if bareexist not in bareexist_to_calibrate_data_dict:
            return None
        calibrate_data = bareexist_to_calibrate_data_dict[bareexist]
        return calibrate_img(img, calibrate_data), calibrate_data['mask']


    def calibrate_m(self, adb_img, mask_hwaf1):
        img, wh = self.get_img_wh_m()
        bareexist = get_bareexist(img)
        logger.debug(f'BACGWQPWBP bareexist={bareexist}')
        if bareexist in bareexist_to_calibrate_data_dict:
            return
        _detect_bar_color(img)
        self._detect_bg_color_m()
        self.fix_target_wh_m()
        
        img, wh = self.get_img_wh_m()

        adb_bgr = adb_img[:,:,:3]

        h,w = img.shape[:2]

        img10 = np.equal(img, bar_color).all(axis=2)
        img11 = np.equal(img, bg_color).all(axis=2)
        img1 = np.logical_or(img10, img11)

        y_sum = img1.sum(axis=1)
        y_not_bar = (y_sum < w//4)
        y_not_bar[0] = False
        game_y0 = int(y_not_bar.nonzero()[0][0])

        x_sum = img1.sum(axis=0)
        x_bar = (x_sum > h//4)
        x_bar[-1] = True
        x_bar_idx_list = x_bar.nonzero()[0]
        game_x1 = int(x_bar_idx_list[0])

        game_x0 = 1
        game_y1 = h-1

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
        logger.debug(f'KQMXMROXWP src_yyxx: {src_yyxx}')

        dest_yyxx = best_i, best_i+game_h, best_j, best_j+game_w
        logger.debug(f'RRGNMXMUWZ dest_yyxx: {dest_yyxx}')

        calibrate_data = {
            'mask': target_mask_hwa,
            'src_yyxx': src_yyxx,
            'dest_yyxx': dest_yyxx,
        }
        bareexist_to_calibrate_data_dict[bareexist] = calibrate_data

    def require_calibrate(self):
        # logger.debug(f'OFFABARANL require_calibrate last_img_bareexist: {self.last_img_bareexist}')
        if self.last_img_bareexist is None:
            return True
        return self.last_img_bareexist not in bareexist_to_calibrate_data_dict

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
        img, wh = self.get_img_wh_m()
        bareexist = get_bareexist(img)
        self._change_wh_m(bareexist_to_target_outer_wh_dict[bareexist])

    def _detect_target_outer_wh_m(self):
        img, wh = self.get_img_wh_m()
        bareexist = get_bareexist(img)
        if bareexist not in bareexist_to_target_outer_wh_dict:
            target_outer_wh = self.__detect_target_outer_wh_m()
            bareexist_to_target_outer_wh_dict[bareexist] = target_outer_wh

    def __detect_target_outer_wh_m(self):
        self._detect_bg_color_m()
        img, wh = self.get_img_wh_m()
        bar_n, bar_e = get_bar_ne(img)

        # find target_outer_width
        le = TARGET_INNER_W - 20
        g = TARGET_INNER_W + bar_e + 20

        while g-le > 1:
            m = (le+g)//2
            img = self._change_wh_m((m,TARGET_INNER_H + bar_n + 20))
            img1 = np.equal(img, bg_color).all(axis=2)
            y_sum = img1.sum(axis=1)
            y_bg = (y_sum > m//4)
            x0 = 250
            while (not y_bg[x0]):
                x0 -= 1
            x0 += 1
            x1 = 250
            while (not y_bg[x1]):
                x1 += 1
            game_h = x1 - x0
            if game_h > TARGET_INNER_H:
                g = m
            else:
                le = m
        target_outer_width = le

        le = TARGET_INNER_H - 20
        g = TARGET_INNER_H + bar_n + 20

        while g-le > 1:
            m = (le+g)//2
            img = self._change_wh_m((TARGET_INNER_W + bar_e + 20,m))
            img1 = np.equal(img, bg_color).all(axis=2)
            x_sum = img1.sum(axis=0)
            x_bg = (x_sum > m//4)
            y0 = 250
            while (not x_bg[y0]):
                y0 -= 1
            y0 += 1
            y1 = 250
            while (not x_bg[y1]):
                y1 += 1
            game_w = y1 - y0
            if game_w > TARGET_INNER_W:
                g = m
            else:
                le = m
        
        target_outer_height = le

        return target_outer_width, target_outer_height

    def _detect_bg_color_m(self):
        if bg_color is not None:
            return
        img, wh = self.get_img_wh_m()
        bar_ne = get_bar_ne(img)
        img = self._change_wh_m((TARGET_INNER_W+40+bar_ne[1],TARGET_INNER_H+bar_ne[0]))
        _detect_bg_color(img)

    def _change_wh_m(self, wh):
        while True:
            self.game_window.size = wh
            ret_img, img_wh = self.get_img_wh_m()
            if img_wh == wh:
                return ret_img

    def _atexit(self):
        if self.windows_capture_control is not None:
            self.windows_capture_control.stop()
            self.windows_capture_control = None

    def _windows_capture__frame_handler(self, frame: Frame, capture_control: InternalCaptureControl):
        frame.save_as_image("tmp.png")
        with self.img_condition:
            self.img_tmp = frame.frame_buffer
            self.img_condition.notify()

    def _windows_capture__closed_handler(self):
        print("Capture Session Closed")
        if self.windows_capture_control is not None:
            self.windows_capture_control.stop()
            self.windows_capture_control = None
            atexit.unregister(self._atexit)


def calibrate_img(img, calibrate_data):
    sy0, sy1, sx0, sx1 = calibrate_data['src_yyxx']
    dy0, dy1, dx0, dx1 = calibrate_data['dest_yyxx']

    ret_img = np.zeros((TARGET_INNER_H, TARGET_INNER_W, 3), np.uint8)
    ret_img[dy0:dy1, dx0:dx1] = img[sy0:sy1, sx0:sx1, :3]

    # common.cv2_imwrite('calibrate_img.png', ret_img)

    return ret_img


def get_bareexist(img):
    bar_ne = get_bar_ne(img)
    return bar_ne[1] > 4


def get_bar_ne(img):
    _detect_bar_color(img)

    img1 = np.equal(img, bar_color).all(axis=2)
    h,w = img1.shape

    y_sum = img1.sum(axis=1)
    y_not_bar = (y_sum < w//4)
    y_not_bar[0] = False
    y_not_bar_idx = int(y_not_bar.nonzero()[0][0])
    bar_n = y_not_bar_idx

    x_sum = img1.sum(axis=0)
    x_bar = (x_sum > h//4)
    x_bar[-1] = True
    x_bar_idx_list = x_bar.nonzero()[0]
    x_bar_idx = int(x_bar_idx_list[0])
    bar_e = w - x_bar_idx

    return bar_n, bar_e

def _detect_bar_color(img):
    global bar_color
    if bar_color is not None:
        return
    bar_color = _top_count_color(img[1:3])
    logger.debug(f'KKZHHDZLRF bar_color: {bar_color}')

def _detect_bg_color(img):
    global bg_color
    if bg_color is not None:
        return
    bg_color = _top_count_color(img[:, 1:3])
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
        bar_ne = get_bar_ne(img)
        print(f'bar_ne: {bar_ne}')
        agent.fix_target_wh_m()
        time.sleep(0.5)

if __name__ == "__main__":
    main()
