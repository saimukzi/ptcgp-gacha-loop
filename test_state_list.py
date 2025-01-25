import argparse
import common
import concurrent.futures as cf
import const
import os
import state_list
# import threading

def main():
    parser = argparse.ArgumentParser(description='Test state_list')
    parser.add_argument('--state', help='state name', nargs='?', default=None)
    args = parser.parse_args()

    state_list.load_state()

    states_path = os.path.join(const.MY_PATH, 'testcases', 'states')

    state_fn_list = []
    for state_name in os.listdir(states_path):
        if args.state is not None and state_name != args.state:
            continue
        state_path = os.path.join(states_path, state_name)
        for fn in os.listdir(state_path):
            if not fn.endswith('.png'):
                continue
            img_fn = os.path.join(state_path, fn)
            state_fn_list.append((state_name, img_fn))
    
    def process_state_fn(state_fn):
        state_name, img_fn = state_fn
        img = common.cv2_imread(img_fn)
        state = state_list.get_state(img, None)
        print(f'{state_name}: {img_fn} -> {state}')
        assert(state == state_name)

    executor = cf.ThreadPoolExecutor()
    ret_itr = executor.map(process_state_fn, state_fn_list)
    for ret in ret_itr:
        pass

if __name__ == '__main__':
    main()
