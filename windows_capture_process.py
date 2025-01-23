import multiprocessing as mp
import my_logger
import numpy as np
import queue
import repeat_timer
import threading

logger = my_logger.logger

class WindowsCaptureProcess:

    def __init__(self, window_name, config_data):
        self.window_name = window_name
        self.config_data = config_data

        self.active = False
        self.alive_time = repeat_timer.RepeatTimer(10, self.keep_process_alive)
        self.condition = threading.Condition()
        self.p2c_queue = None
        self.c2p_queue = None
        self.call_id = 0
        self.process = None

    def start(self):
        with self.condition:
            self.active = True
            self.keep_process_alive()
            self.alive_time.start()

    def stop(self):
        with self.condition:
            self.active = False
            self.call(('stop',))
            self.alive_time.stop()
            if self.process is not None:
                self.process.join()
            self.process = None
            self.p2c_queue = None
            self.c2p_queue = None

    # return None if fail
    def call(self, args, ret=False):
        with self.condition:
            if not self.active:
                return None
            my_call_id = self.call_id
            self.call_id += 1
            self.call_id %= 1000
            self.p2c_queue.put((my_call_id, *args))
            if ret:
                try:
                    while True:
                        v = self.c2p_queue.get(block=True, timeout=5)
                        if v[0] == my_call_id:
                            return v[1:]
                except queue.Empty:
                    return None

    def keep_process_alive(self):
        logger.debug('JPALMPDQZH keep_process_alive')
        with self.condition:
            # logger.debug('XHESPDJOAZ keep_process_alive 2')
            if not self.active:
                return
            # logger.debug('XHESPDJOAZ keep_process_alive 3')
            if self.process is not None:
                if self.process.is_alive():
                    return
                try:
                    self.process.close()
                except:
                    pass
            # logger.debug('XHESPDJOAZ keep_process_alive 4')
            self.p2c_queue = mp.Queue()
            self.c2p_queue = mp.Queue()
            self.process = mp.Process(target=process_run, args=(self.window_name, self.config_data, self.p2c_queue, self.c2p_queue))
            self.process.start()

    # return None if fail
    def get_frame(self, nnext=False):
        call_ret = self.call(('get_img_data', nnext), ret=True)
        if call_ret is None:
            return None
        if (len(call_ret)==1) and (call_ret[0]==None):
            return None
        idx, b, shape = call_ret
        ret_np = np.frombuffer(b, dtype=np.uint8).reshape(*shape)
        return ret_np, idx

def process_run(window_name, config_data, p2c_queue, c2p_queue):
    # import multiprocessing as mp
    # import threading
    import atexit
    import time
    from windows_capture import WindowsCapture, Frame, InternalCaptureControl

    my_logger.update_logger(config_data)

    parent_process = mp.parent_process()

    condition = threading.Condition()
    windows_capture_control = None
    img_data_tmp = None
    img_idx = 0
    closed = False

    capture = WindowsCapture(
        cursor_capture=False,
        draw_border=None,
        monitor_index=None,
        window_name=window_name,
    )

    @capture.event
    def on_frame_arrived(frame: Frame, capture_control: InternalCaptureControl):
        nonlocal img_data_tmp
        nonlocal img_idx

        if (not frame.frame_buffer.any()):
            logger.warning('KGRWTXPIIJ zero content')
            return
        with condition:
            img_data_tmp = {
                'img': frame.frame_buffer,
                'idx': img_idx,
            }
            img_idx += 1
            img_idx %= 1000
            condition.notify()

    @capture.event
    def on_closed():
        nonlocal closed
        logger.debug("AOIXXTFNAF Capture Session Closed")
        closed = True

    def my_atexit():
        logger.debug('RBIOZFXZXD exit')
        if windows_capture_control is not None:
            windows_capture_control.stop()
    atexit.register(my_atexit)
    windows_capture_control = capture.start_free_threaded()

    last_img_idx = None
    while True:
        try:
            my_logger.update_logger(config_data)
            if not parent_process.is_alive():
                logger.debug('SUHPDEWUQG parent dead')
                windows_capture_control.stop()
                break
            cmd = p2c_queue.get(block=True, timeout=1)
            # logger.debug(f'OBILGITORA {cmd}')
            call_id = cmd[0]
            if cmd[1] == 'stop':
                windows_capture_control.stop()
                break
            elif cmd[1] == 'get_img_data':
                nnext = cmd[2]
                if not nnext:
                    with condition:
                        ret_img_data = img_data_tmp
                    if ret_img_data is not None:
                        last_img_idx = ret_img_data['idx']
                    if ret_img_data is None:
                        c2p_queue.put((call_id, None), timeout=1)
                    else:
                        c2p_queue.put((call_id, ret_img_data['idx'], ret_img_data['img'].tobytes(), ret_img_data['img'].shape), timeout=1)
                else:
                    deadline = time.time() + 1
                    while True:
                        with condition:
                            good = True
                            ret_img_data = img_data_tmp
                            if good:
                                good = ret_img_data is not None
                            if good:
                                good = last_img_idx != ret_img_data['idx']
                            if good:
                                last_img_idx = ret_img_data['idx']
                                c2p_queue.put((call_id, ret_img_data['idx'], ret_img_data['img'].tobytes(), ret_img_data['img'].shape), timeout=1)
                                break
                            # not good
                            if time.time() >= deadline:
                                # give up
                                c2p_queue.put((call_id, None), timeout=1)
                                break
                            condition.wait(deadline-time.time())

        except queue.Empty:
            pass

        if closed:
            break