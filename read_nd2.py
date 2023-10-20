from module import nd2
import numpy as np
import cv2
from nd2reader import ND2Reader


def read_nd2(filepath, option='mean'):
    with nd2.ND2File(filepath) as ndfile:
        with ND2Reader(filepath) as nd:
            green = np.array([np.array(ndfile)[x][0] for x in range(ndfile.shape[0])]).astype(np.double)
            red = np.array([np.array(ndfile)[x][1] for x in range(ndfile.shape[0])]).astype(np.double)
            trans = np.array([np.array(ndfile)[x][2] for x in range(ndfile.shape[0])]).astype(np.double)

            for i, (r, g, t) in enumerate(zip(red, green, trans)):
                red[i] = r / np.max(r)
                green[i] = g / np.max(g)
                trans[i] = t / np.max(t)

            red = np.array(np.stack([red, np.zeros(red.shape), np.zeros(red.shape)], axis=3) * 255).astype(np.uint8)
            green = np.array(np.stack([np.zeros(green.shape), green, np.zeros(green.shape)], axis=3) * 255).astype(
                np.uint8)
            trans = np.array(np.stack([np.zeros(trans.shape), np.zeros(trans.shape), trans], axis=3) * 255).astype(
                np.uint8)
    return red, green, trans, (red.shape[0], nd.metadata['width'], nd.metadata['height'], nd.metadata['pixel_microns'])
