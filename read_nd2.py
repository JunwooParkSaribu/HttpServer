from module import nd2
import numpy as np
import cv2


def read_nd2(filepath, option='mean'):
    # nd2reader is for metadata
    with nd2.ND2File(filepath) as ndfile:
        green = np.array([np.array(ndfile)[x][0] for x in range(ndfile.shape[0])])
        red = np.array([np.array(ndfile)[x][1] for x in range(ndfile.shape[0])])
        trans = np.array([np.array(ndfile)[x][2] for x in range(ndfile.shape[0])])

        # z-projection
        if option == 'mean':
            red = (np.array(red / np.max(red))).mean(axis=0)
            green = (np.array(green / np.max(green))).mean(axis=0)
            trans = (np.array(trans / np.max(trans))).mean(axis=0)
        else:
            red = (np.array(red / np.max(red))).max(axis=0)
            green = (np.array(green / np.max(green))).max(axis=0)
            trans = (np.array(trans / np.max(trans))).max(axis=0)

        # Stacking
        red = np.array(np.stack([red, np.zeros(red.shape), np.zeros(red.shape)], axis=2) * 255).astype(np.uint8)
        green = np.array(np.stack([np.zeros(green.shape), green, np.zeros(green.shape)], axis=2) * 255).astype(np.uint8)
        trans = np.array(np.stack([np.zeros(trans.shape), np.zeros(trans.shape), trans], axis=2) * 255).astype(np.uint8)
    return red, green, trans
