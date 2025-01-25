import atexit
import multiprocessing as mp
import my_logger
import numpy as np
import queue
import time
import traceback
# import repeat_timer
import threading

logger = my_logger.logger

class WindowsCaptureProcess:

    def __init__(self, window_name, config_data):
        self.window_name = window_name
        self.config_data = config_data

        self.active = False
        # self.alive_timer = repeat_timer.RepeatTimer(10, self.keep_process_alive)
        # self.condition = threading.Condition()
        self.p2c_queue = None
        self.c2p_queue = None
        self.call_id = 0
        self.process = None

    def start(self):
        # with self.condition:
        self.active = True
        self.keep_process_alive()
        # self.alive_timer.start()

    def stop(self):
        # with self.condition:
        self.active = False
        try:
            self.call(('stop',))
        except:
            pass
        # self.alive_timer.stop()
        try:
            if self.process is not None:
                self.process.terminate()
                self.process.join()
                self.process.close()
        except:
            pass
        self.process = None
        self.p2c_queue = None
        self.c2p_queue = None

    # NotActiveException
    # ProcessDownException
    # RPCTimeoutException
    def call(self, args, ret=False):
        # with self.condition:
        if not self.active:
            raise NotActiveException()
        my_call_id = self.call_id
        self.call_id += 1
        self.call_id %= 1000
        if not self.process.is_alive():
            raise ProcessDownException()
        self.p2c_queue.put((my_call_id, *args))
        if ret:
            deadline = time.time() + 5
            while True:
                try:
                    time_remain = deadline - time.time()
                    if time_remain <= 0:
                        raise RPCTimeoutException()
                    if not self.process.is_alive():
                        raise ProcessDownException()
                    call_id, exc, ret = self.c2p_queue.get(block=True, timeout=min(0.1,time_remain))
                    if call_id != my_call_id: continue
                    if exc is not None:
                        raise TXT_TO_EXCEPTION[exc]()
                    return ret
                except queue.Empty:
                    pass

    def keep_process_alive(self):
        logger.debug('JPALMPDQZH keep_process_alive')
        # with self.condition:
        # logger.debug('XHESPDJOAZ keep_process_alive 2')
        if not self.active:
            return
        # logger.debug('XHESPDJOAZ keep_process_alive 3')
        if self.process is not None:
            if self.process.is_alive():
                return
            try:
                self.process.terminate()
                self.process.join()
                self.process.close()
            except:
                logger.warning(f'AZTLFHLLHL process close error')
                traceback.print_exc()
            self.process = None
        # logger.debug('XHESPDJOAZ keep_process_alive 4')
        self.p2c_queue = mp.Queue()
        self.c2p_queue = mp.Queue()
        self.process = mp.Process(target=process_run, args=(self.window_name, self.config_data, self.p2c_queue, self.c2p_queue))
        self.process.start()

    # NotActiveException
    # ProcessDownException
    # RPCTimeoutException
    # FrameTimeoutException
    def get_frame(self, nnext=False):
        call_ret = self.call(('get_img_data', nnext), ret=True)
        # if call_ret is None:
        #     return None
        # if (len(call_ret)==1) and (call_ret[0]==None):
        #     return None
        idx, b, shape = call_ret
        ret_np = np.frombuffer(b, dtype=np.uint8).reshape(*shape)
        return ret_np, idx

DEADMAN_SEC = 30

def process_run(window_name, config_data, p2c_queue, c2p_queue):
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

    deadman_time = time.time() + DEADMAN_SEC

    last_img_idx = None
    while True:
        try:
            my_logger.update_logger(config_data)
            if not parent_process.is_alive():
                logger.debug('SUHPDEWUQG parent dead')
                break
            if time.time() >= deadman_time:
                logger.debug('QOVKCHADMJ deadman switch')
                break
            cmd = p2c_queue.get(block=True, timeout=1)
            deadman_time = time.time() + DEADMAN_SEC
            # logger.debug(f'OBILGITORA {cmd}')
            call_id = cmd[0]
            if cmd[1] == 'stop':
                logger.debug('SGBUSHEPVD stop cmd')
                break
            elif cmd[1] == 'get_img_data':
                # input nnext
                # return idx, b, shape
                nnext = cmd[2]

                deadline = time.time() + 5
                while True:
                    with condition:
                        ret_img_data = img_data_tmp
                        good = True
                        if good:
                            good = ret_img_data is not None
                        if good:
                            good = (last_img_idx != ret_img_data['idx']) or (not nnext)
                        if good:
                            last_img_idx = ret_img_data['idx']
                            c2p_queue.put_nowait((call_id, None, (ret_img_data['idx'], ret_img_data['img'].tobytes(), ret_img_data['img'].shape)))
                            break
                        # not good
                        if time.time() >= deadline:
                            # give up
                            c2p_queue.put_nowait((call_id, 'FrameTimeoutException', None))
                            break
                        condition.wait(max(0,deadline-time.time()))

        except queue.Empty:
            pass

        if closed:
            break

    windows_capture_control.stop()

class NotActiveException(Exception):
    pass

class ProcessDownException(Exception):
    pass

class RPCTimeoutException(Exception):
    pass

class FrameTimeoutException(Exception):
    pass

TXT_TO_EXCEPTION = {}
TXT_TO_EXCEPTION['NotActiveException'] = NotActiveException
TXT_TO_EXCEPTION['ProcessDownException'] = ProcessDownException
TXT_TO_EXCEPTION['RPCTimeoutException'] = RPCTimeoutException
TXT_TO_EXCEPTION['FrameTimeoutException'] = FrameTimeoutException
