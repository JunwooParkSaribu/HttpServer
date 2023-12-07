from module import nd2
import numpy as np
from nd2reader import ND2Reader
from czifile import CziFile
import scipy
import skimage
import tifffile


def read_nd2(filepath, option='mean'):
    with nd2.ND2File(filepath) as ndfile:
        with ND2Reader(filepath) as nd:
            greens = np.array([np.array(ndfile)[x][0] for x in range(ndfile.shape[0])]).astype(np.double)
            reds = np.array([np.array(ndfile)[x][1] for x in range(ndfile.shape[0])]).astype(np.double)
            transs = np.array([np.array(ndfile)[x][2] for x in range(ndfile.shape[0])]).astype(np.double)

            r_max = np.mean(np.max(reds, axis=(1, 2)))
            g_max = np.mean(np.max(greens, axis=(1, 2)))
            t_max = np.mean(np.max(transs, axis=(1, 2)))

            original_y_size = reds.shape[1]
            original_x_size = reds.shape[2]
            downsampling_x = int(original_x_size / 256.)
            downsampling_y = int(original_y_size / 256.)

            reds = skimage.measure.block_reduce(reds, (1, downsampling_x, downsampling_y), np.max)
            greens = skimage.measure.block_reduce(greens, (1, downsampling_x, downsampling_y), np.max)
            transs = skimage.measure.block_reduce(transs, (1, downsampling_x, downsampling_y), np.max)
            y_size = reds.shape[1]
            x_size = reds.shape[2]
            zero_base = np.zeros((y_size, x_size), dtype=np.uint8)
            one_base = np.ones((y_size, x_size), dtype=np.uint8)

            for i, (r, g, t) in enumerate(zip(reds, greens, transs)):
                r_mode = scipy.stats.mode(r.reshape(r.shape[0] * r.shape[1]), keepdims=False)[0]
                g_mode = scipy.stats.mode(g.reshape(g.shape[0] * g.shape[1]), keepdims=False)[0]
                t_mode = scipy.stats.mode(t.reshape(t.shape[0] * t.shape[1]), keepdims=False)[0]
                r = r - r_mode
                g = g - g_mode
                t = t - t_mode
                r_min = np.min(r)
                g_min = np.min(g)
                t_min = np.min(t)
                r = np.maximum(r, zero_base)
                g = np.maximum(g, zero_base)
                t = np.maximum(t, zero_base)
                r = r / (r_max - r_min)
                g = g / (g_max - g_min)
                t = t / (t_max - t_min)
                r = np.minimum(r, one_base)
                g = np.minimum(g, one_base)
                t = np.minimum(t, one_base)
                reds[i] = r
                greens[i] = g
                transs[i] = t

            red = np.array(np.stack([reds, np.zeros(reds.shape), np.zeros(reds.shape)], axis=3) * 255).astype(np.uint8)
            green = np.array(np.stack([np.zeros(greens.shape), greens, np.zeros(greens.shape)], axis=3) * 255).astype(
                np.uint8)
            trans = np.array(np.stack([np.zeros(transs.shape), np.zeros(transs.shape), transs], axis=3) * 255).astype(
                np.uint8)
    return red, green, trans, {'zDepth': red.shape[0], 'xSize': nd.metadata['width'], 'ySize': nd.metadata['height'],
                               'pixelType': 'Unknown', 'dyeName': 'Unknown', 'dyeId': 'Unknown',
                               'pixelMicrons': nd.metadata['pixel_microns'], 'time': 'Unknown'}


def read_czi(filepath):
    with CziFile(filepath) as czi:
        metadata = czi.metadata()
        pixelType = metadata.split('<PixelType>')[1].split('</PixelType>')[0]
        dyeName = metadata.split('<DyeName>')[1].split('</DyeName>')[0]
        dyeId = metadata.split('<DyeId>')[1].split('</DyeId>')[0]
        time = metadata.split('<Time>')[1].split('</Time>')[0]
        del metadata

        img = czi.asarray()
        nb_channel = img.shape[1]
        z_depth = img.shape[2]
        original_y_size = img.shape[3]
        original_x_size = img.shape[4]
        downsampling_x = int(original_x_size / 256.)
        downsampling_y = int(original_y_size / 256.)

        if img.shape[0] == 1 and img.shape[5] == 1:
            img = img.reshape((nb_channel, z_depth, original_y_size, original_x_size))
        else:
            print('czi file array format recheck')
            exit(1)
        reds = np.array(img[0]).astype(np.double)
        greens = np.array(img[1]).astype(np.double)
        reds = skimage.measure.block_reduce(reds, (1, downsampling_x, downsampling_y), np.max)
        greens = skimage.measure.block_reduce(greens, (1, downsampling_x, downsampling_y), np.max)
        y_size = reds.shape[1]
        x_size = reds.shape[2]
        zero_base = np.zeros((y_size, x_size), dtype=np.uint8)
        one_base = np.ones((y_size, x_size), dtype=np.uint8)
        del img

        r_max = np.max(reds, axis=(1, 2))
        g_max = np.max(greens, axis=(1, 2))
        g_max = np.mean(g_max)
        r_max = np.mean(r_max)
        for i, (r, g) in enumerate(zip(reds, greens)):
            r_mode = scipy.stats.mode(r.reshape(r.shape[0] * r.shape[1]), keepdims=False)[0]
            g_mode = scipy.stats.mode(g.reshape(g.shape[0] * g.shape[1]), keepdims=False)[0]
            r = r - r_mode
            g = g - g_mode
            r_min = np.min(r)
            g_min = np.min(g)
            r = np.maximum(r, zero_base)
            g = np.maximum(g, zero_base)
            r = r / (r_max - r_min)
            g = g / (g_max - g_min)
            r = np.minimum(r, one_base)
            g = np.minimum(g, one_base)
            reds[i] = r
            greens[i] = g
        reds = np.array(np.stack([reds, np.zeros(reds.shape), np.zeros(reds.shape)],
                                 axis=3) * 255, dtype=np.uint8)
        greens = np.array(np.stack([np.zeros(greens.shape), greens, np.zeros(greens.shape)],
                                   axis=3) * 255, dtype=np.uint8)

    return reds, greens, {'zDepth': z_depth, 'xSize': original_x_size, 'ySize': original_y_size,
                          'pixelType': pixelType, 'dyeName': dyeName, 'dyeId': dyeId, 'pixelMicrons': 'Unknown',
                          'time': time}


def read_tif(filepath):
    reds = []
    greens = []
    imgs = tifffile.imread(filepath).astype(np.double)
    z_depth = imgs.shape[0]
    for z_level in range(z_depth):
        reds.append(imgs[z_level][0])
        greens.append(imgs[z_level][1])
    reds = np.array(reds)
    greens = np.array(greens)

    original_y_size = reds.shape[1]
    original_x_size = reds.shape[2]
    downsampling_x = int(original_x_size / 256.)
    downsampling_y = int(original_y_size / 256.)
    reds = skimage.measure.block_reduce(reds, (1, downsampling_x, downsampling_y), np.max)
    greens = skimage.measure.block_reduce(greens, (1, downsampling_x, downsampling_y), np.max)

    y_size = reds.shape[1]
    x_size = reds.shape[2]
    zero_base = np.zeros((y_size, x_size), dtype=np.uint8)
    one_base = np.ones((y_size, x_size), dtype=np.uint8)
    r_max = np.mean(np.max(reds, axis=(1, 2)))
    g_max = np.mean(np.max(greens, axis=(1, 2)))

    for i, (r, g) in enumerate(zip(reds, greens)):
        r_mode = scipy.stats.mode(r.reshape(r.shape[0] * r.shape[1]), keepdims=False)[0]
        g_mode = scipy.stats.mode(g.reshape(g.shape[0] * g.shape[1]), keepdims=False)[0]
        r = r - r_mode
        g = g - g_mode
        r = np.maximum(r, zero_base)
        g = np.maximum(g, zero_base)
        r_min = np.min(r)
        g_min = np.min(g)
        r = r / (r_max - r_min)
        g = g / (g_max - g_min)
        r = np.minimum(r, one_base)
        g = np.minimum(g, one_base)
        reds[i] = r
        greens[i] = g
    reds = np.array(np.stack([reds, np.zeros(reds.shape), np.zeros(reds.shape)], axis=3) * 255).astype(np.uint8)
    greens = np.array(np.stack([np.zeros(greens.shape), greens, np.zeros(greens.shape)], axis=3) * 255).astype(
        np.uint8)

    return reds, greens, {'zDepth': z_depth, 'xSize': original_x_size, 'ySize': original_y_size,
                          'pixelType': 'Unknown', 'dyeName': 'Unknown', 'dyeId': 'Unknown', 'pixelMicrons': 'Unknown'}
