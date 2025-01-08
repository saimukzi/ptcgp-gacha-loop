import cv2
import numpy as np
import os

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
    bytess = cv2.imencode('.png', img, params=params)[1].tobytes()
    with open(file_path, 'wb') as f:
        f.write(bytess)
