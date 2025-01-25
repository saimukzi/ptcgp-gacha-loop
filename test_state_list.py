import argparse
import common
import const
import os
import state_list

def main():
    parser = argparse.ArgumentParser(description='Test state_list')
    parser.add_argument('--state', help='state name', nargs='?', default=None)
    args = parser.parse_args()

    state_list.load_state()

    states_path = os.path.join(const.MY_PATH, 'testcases', 'states')

    for state_name in os.listdir(states_path):
        if args.state is not None and state_name != args.state:
            continue
        state_path = os.path.join(states_path, state_name)
        for fn in os.listdir(state_path):
            if not fn.endswith('.png'):
                continue
            img_fn = os.path.join(state_path, fn)
            img = common.cv2_imread(img_fn)
            state = state_list.get_state(img, None)
            print(f'{state_name}: {fn} -> {state}')
            assert(state == state_name)
        #print(state)

if __name__ == '__main__':
    main()
