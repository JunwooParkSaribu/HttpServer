from module import nd2
import numpy as np
import cv2
from nd2reader import ND2Reader
from czifile import CziFile


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
    return red, green, trans, {'zDepth': red.shape[0], 'xSize': nd.metadata['width'], 'ySize': nd.metadata['height'],
                               'pixelType': 'Unknown', 'dyeName': 'Unknown', 'dyeId': 'Unknown',
                               'pixelMicrons': nd.metadata['pixel_microns']}


def read_czi(filepath):
    with CziFile(filepath) as czi:
        metadata = czi.metadata()
        pixelType = metadata.split('<PixelType>')[1].split('</PixelType>')[0]
        dyeName = metadata.split('<DyeName>')[1].split('</DyeName>')[0]
        dyeId = metadata.split('<DyeId>')[1].split('</DyeId>')[0]
        img = czi.asarray()
        nb_channel = img.shape[1]
        z_depth = img.shape[2]
        y_size = img.shape[3]
        x_size = img.shape[4]
        if img.shape[0] == 1 and img.shape[5] == 1:
            img = img.reshape((nb_channel, z_depth, y_size, x_size))
        else:
            print('czi file array format recheck')
            exit(1)
        reds = np.array(img[0]).astype(np.double)
        greens = np.array(img[1]).astype(np.double)

        for i, (r, g) in enumerate(zip(reds, greens)):
            r_min = np.min(r)
            r_max = np.max(r)
            g_min = np.min(g)
            g_max = np.max(g)
            reds[i] = (r - r_min) / (r_max - r_min)
            greens[i] = (g - g_min) / (r_max - r_min)

        reds = np.array(np.stack([reds, np.zeros(reds.shape), np.zeros(reds.shape)], axis=3) * 255).astype(np.uint8)
        greens = np.array(np.stack([np.zeros(greens.shape), greens, np.zeros(greens.shape)], axis=3) * 255).astype(
            np.uint8)

    return reds, greens, {'zDepth': z_depth, 'xSize': x_size, 'ySize': y_size,
                          'pixelType': pixelType, 'dyeName': dyeName, 'dyeId': dyeId, 'pixelMicrons': 'Unknown'}
