import argparse

import cv2

import state_list

def main():
    parser = argparse.ArgumentParser(description='Check state')
    parser.add_argument('filename', type=str)
    args = parser.parse_args()
    
    img = cv2.imread(args.filename)

    state_list.load_state()
    state_list.get_state(img, debug=True)

if __name__ == '__main__':
    main()
