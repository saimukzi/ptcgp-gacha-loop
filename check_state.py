import argparse
import common
import state_list

def main():
    parser = argparse.ArgumentParser(description='Check state')
    parser.add_argument('filename', type=str)
    parser.add_argument('--mask', type=str, nargs='?', default=None)
    args = parser.parse_args()
    
    img = common.cv2_imread(args.filename)

    state_mask = None
    if args.mask is not None:
        state_mask = set(args.mask.split(','))

    state_list.load_state()
    state_list.get_state(img, None, state_mask=state_mask, debug=True)

if __name__ == '__main__':
    main()
