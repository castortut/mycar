#!/usr/bin/env python3
"""
Scripts to drive a donkey 2 car and train a model for it.

Usage:
    manage.py (drive) [--model=<model>] [--js] [--chaos]
    manage.py (train) [--tub=<tub1,tub2,..tubn>]  (--model=<model>) [--base_model=<base_model>] [--no_cache]

Options:
    -h --help        Show this screen.
    --tub TUBPATHS   List of paths to tubs. Comma separated. Use quotes to use wildcards. ie "~/tubs/*"
    --js             Use physical joystick.
    --chaos          Add periodic random steering when manually driving
"""
import os
import sys
import time
import copy
import argparse
import random
from donkeycar.parts.datastore import TubGroup, Tub
from scipy.ndimage.filters import gaussian_filter
from shutil import copyfile

import numpy as np


CAM_IMG_ARRAY = 'cam/image_array'
USER_ANGLE = 'user/angle'
USER_THROTTLE = 'user/throttle'


def augment_single_record(record, args):
    """
    Modify given record and return modifications in a list.
    Order:
        1. Flipping image (left/right)
        2. Darken the image
        3. Add "sun" (bright area) to the image
        4. Add noise to image
    """
    augmented_records = [record]
    if args.flip:
        augmented_records.append(flip(record))

    darkened_records = list()
    for rec in augmented_records:
        for _ in range(args.dark):
            darkened_records.append(dark(rec, args.dark_amount))

    augmented_records += darkened_records

    sun_records = list()
    for rec in augmented_records:
        for _ in range(args.sun):
            sun_records.append(sun(rec, args.sun_size))

    augmented_records += sun_records

    noise_records = list()
    for rec in augmented_records:
        for _ in range(args.noise):
            noise_records.append(noise(rec, args.noise_amount))

    augmented_records += noise_records

    return augmented_records


def augment(tub_names, new_data_dir, args):

    tubgroup = TubGroup(tub_names)

    if new_data_dir == "aug":
        new_data_dir = os.path.expanduser(new_data_dir)
        new_data_dir_full = os.path.join(os.path.dirname(tubgroup.tubs[0].path), new_data_dir)
    else:
        new_data_dir = os.path.expanduser(new_data_dir)
        new_data_dir_full = new_data_dir


    # If tub directory does not exist, create directory
    if not os.path.exists(new_data_dir):
        os.makedirs(new_data_dir)

    # If directory does not contain meta.json, copy one from the first source tub
    if not os.path.exists(os.path.join(new_data_dir_full, 'meta.json')):
        copyfile(src=tubgroup.tubs[0].meta_path, dst=os.path.join(new_data_dir_full, 'meta.json'))

    new_tub = Tub(new_data_dir_full)

    t0 = time.time()

    i=0
    for tub in tubgroup.tubs:
        for ix in tub.get_index(shuffled=False):
            record = tub.get_record(ix)
            for augmented_record in augment_single_record(record, args):
                new_tub.put_record(augmented_record)
                i=i+1
                if i==1000:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                    i=0
    sys.stdout.write("\nFinished augmenting all records to %s.\n" % (new_data_dir_full) )
    sys.stdout.flush()

    t1 = time.time()
    t_delta_mins = (t1-t0)/60
    sys.stdout.write("It took %f minutes.\n" % (t_delta_mins))


def flip(record):
    flipped = copy.deepcopy(record)
    flipped[CAM_IMG_ARRAY] = record[CAM_IMG_ARRAY][:, ::-1, :]
    flipped[USER_ANGLE] = -record[USER_ANGLE]
    return flipped


def noise(record, amount):
    noised = copy.copy(record)
    img = record[CAM_IMG_ARRAY]
    noise_img = np.random.random_integers(-amount, amount, img.shape)
    noised_img = clip_image_values(img + noise_img)
    noised[CAM_IMG_ARRAY] = noised_img
    return noised


def dark(record, amount):
    darkened = copy.copy(record)
    img = np.array(record[CAM_IMG_ARRAY], dtype=np.int16) - random.randint(1, amount)
    img = clip_image_values(img)
    darkened[CAM_IMG_ARRAY] = img
    return darkened


def sun(record, size):
    sun_added_record = copy.copy(record)
    img = np.array(record[CAM_IMG_ARRAY], dtype=np.int16)
    sun_x = int(random.random() * img.shape[1])
    sun_y = int(random.random() * img.shape[0])
    mask = create_circular_mask(img.shape[0], img.shape[1], [sun_x, sun_y], size)
    mask.dtype = np.uint8
    mask *= 200

    mask = gaussian_filter(mask, sigma=5)

    if len(img.shape) == 2:
        img += mask
    elif len(img.shape) == 3:
        for ii in range(3):
            img[:, :, ii] += mask
    sun_added_record[CAM_IMG_ARRAY] = clip_image_values(img)
    return sun_added_record

def create_circular_mask(h, w, center=None, radius=None):
    """
    https://stackoverflow.com/a/44874588
    :param h:
    :param w:
    :param center:
    :param radius:
    :return:
    """
    if center is None:  # use the middle of the image
        center = [int(w/2), int(h/2)]
    if radius is None:  # use the smallest distance between the center and image walls
        radius = min(center[0], center[1], w-center[0], h-center[1])

    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((X - center[0])**2 + (Y-center[1])**2)

    mask = dist_from_center <= radius
    return mask


def clip_image_values(img):
    img[img > 255] = 255
    img[img < 0] = 0
    return np.array(img, dtype=np.uint8)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--tub', type=str, help='Path of tub, source data')
    parser.add_argument('--dest', type=str, default="aug", help='Path of tub, destination data. Directory is created, if it does not exist. By default: tubdir/../aug')
    parser.add_argument('--flip', action='store_true', help='Augmentation by flipping image left -> right')
    parser.add_argument('--noise', type=int, default=0,
                        help='Augmentation by adding noise to image. Give number of how many times noise is added (how many new records are created from one record)')
    parser.add_argument('--noise_amount', type=int, default=10, help='Amount of noise to be added: by default 1.0 (range [0, 255])')
    parser.add_argument('--dark', type=int, default=0,
                        help='Augmentation by darkening the image. Give number how many times shadow is added (how many new records are created from one record')
    parser.add_argument('--dark_amount', type=int, default=20,
                        help='How much darker image should be. Image is darkened randomly, range is [1, <value>]')
    parser.add_argument('--sun', type=int, default=0,
                        help='Augmentation by adding bright area to image. Give number how many times bright area is added (how many new records are created from one record')
    parser.add_argument('--sun_size', type=int, default=30,
                        help='Size of the bright area')

    args = parser.parse_args()

    augment(args.tub, args.dest, args)
