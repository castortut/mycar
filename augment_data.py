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
import copy
import argparse
import random
from donkeycar.parts.datastore import TubGroup, Tub
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
        2. Shadows to image
        3. Add noise to image
    """
    augmented_records = [record]
    if args.flip:
        augmented_records.append(flip(record))

    shadowed_records = list()
    for rec in augmented_records:
        for _ in range(args.shadow):
            shadowed_records.append(shadow(rec))

    augmented_records += shadowed_records

    noise_records = list()
    for rec in augmented_records:
        for _ in range(args.noise):
            noise_records.append(noise(rec, args.noise_amount))

    augmented_records += noise_records

    return augmented_records


def augment(tub_names, new_data_dir, args):
    new_data_dir = os.path.expanduser(new_data_dir)

    tubgroup = TubGroup(tub_names)

    # If tub directory does not exist, create directory
    if not os.path.exists(new_data_dir):
        os.makedirs(new_data_dir)

    # If directory does not contain meta.json, copy one from the first source tub
    if not os.path.exists(os.path.join(new_data_dir, 'meta.json')):
        copyfile(src=tubgroup.tubs[0].meta_path, dst=os.path.join(new_data_dir, 'meta.json'))

    new_tub = Tub(new_data_dir)

    for tub in tubgroup.tubs:
        for ix in tub.get_index(shuffled=False):
            record = tub.get_record(ix)
            for augmented_record in augment_single_record(record, args):
                new_tub.put_record(augmented_record)


def flip(record):
    flipped = copy.copy(record)
    flipped[CAM_IMG_ARRAY] = record[CAM_IMG_ARRAY][:, ::-1, :]
    flipped[USER_ANGLE] = -record[USER_ANGLE]
    return flipped


def noise(record, amount):
    noised = copy.copy(record)
    img = record[CAM_IMG_ARRAY]
    noise_img = np.random.random_integers(-amount, amount, img.shape)
    noised_img = clip_image_to_range(img + noise_img)
    noised[CAM_IMG_ARRAY] = noised_img
    return noised


def shadow(record):
    shadowed = copy.copy(record)
    img = record[CAM_IMG_ARRAY]



    shadowed[CAM_IMG_ARRAY] = record[CAM_IMG_ARRAY]
    return copy.copy(record)


def clip_image_to_range(img, low=0, high=255):
    img[img > high] = high
    img[img < low] = low
    return img


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--tub', type=str, help='Path of tub, source data')
    parser.add_argument('--dest', type=str, help='Path of tub, destination data. Directory is created, if it does not exist.')
    parser.add_argument('--flip', action='store_true', help='Augmentation by flipping image left -> right')
    parser.add_argument('--noise', type=int, default=0,
                        help='Augmentation by adding noise to image. Give number of how many times noise is added (how many new records are created from one record)')
    parser.add_argument('--noise_amount', type=int, default=10, help='Amount of noise to be added: by default 1.0 (range [0, 255])')
    parser.add_argument('--shadow', type=int, default=0,
                        help='Augmentation by adding shadow to image. Give number how many times shadow is added (how many new records are created from one record')
    parser.add_argument('--sun', type=int, default=0,
                        help='Augmentation by adding bright area to image. Give number how many times bright area is added (how many new records are created from one record')

    args = parser.parse_args()

    augment(args.tub, args.dest, args)
