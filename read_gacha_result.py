import argparse
import card_list

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('img_path')
    args = parser.parse_args()

    card_list.load_card_img()
    img = card_list.common.cv2_imread(args.img_path)
    card_list.read_gacha_result(img)

if __name__ == '__main__':
    main()
