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
from donkeycar.parts.datastore import TubGroup, Tub
from shutil import copyfile


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
            noise_records.append(noise(rec))

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
    flipped['cam/image_array'] = record['cam/image_array'][:, ::-1, :]
    flipped['user/angle'] = -record['user/angle']
    return flipped


def noise(record):
    return copy.copy(record)


def shadow(record):
    shadowed = copy.copy(record)
    shadowed['cam/image_array'] = record['cam/image_array']
    return copy.copy(record)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--flip', action='store_false')
    parser.add_argument('--noise', action='store_const', const=0, default=0)
    parser.add_argument('--shadow', action='store_const', const=0, default=0)

    args = parser.parse_args()

    augment('tub_small', 'tub2', args)
