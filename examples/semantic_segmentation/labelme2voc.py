#!/usr/bin/env python

from __future__ import print_function

import argparse
import glob
import io
import json
import os
import os.path as osp

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np
import PIL.Image
import PIL.ImagePalette
import skimage.color
import skimage.io

import labelme
from labelme.utils import label2rgb
from labelme.utils import label_colormap


# TODO(wkentaro): Move to labelme/utils.py
# contrib
# -----------------------------------------------------------------------------


def labelme_shapes_to_label(img_shape, shapes, label_name_to_value):
    lbl = np.zeros(img_shape[:2], dtype=np.int32)
    for shape in shapes:
        polygons = shape['points']
        label_name = shape['label']
        if label_name in label_name_to_value:
            label_value = label_name_to_value[label_name]
        else:
            label_value = len(label_name_to_value)
            label_name_to_value[label_name] = label_value
        mask = labelme.utils.polygons_to_mask(img_shape[:2], polygons)
        lbl[mask] = label_value

    return lbl


def draw_label(label, img, label_names, colormap=None):
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0,
                        wspace=0, hspace=0)
    plt.margins(0, 0)
    plt.gca().xaxis.set_major_locator(plt.NullLocator())
    plt.gca().yaxis.set_major_locator(plt.NullLocator())

    if colormap is None:
        colormap = label_colormap(len(label_names))

    label_viz = label2rgb(
        label, img, n_labels=len(label_names), alpha=.5)
    plt.imshow(label_viz)
    plt.axis('off')

    plt_handlers = []
    plt_titles = []
    for label_value, label_name in enumerate(label_names):
        if label_value not in label:
            continue
        if label_name.startswith('_'):
            continue
        fc = colormap[label_value]
        p = plt.Rectangle((0, 0), 1, 1, fc=fc)
        plt_handlers.append(p)
        plt_titles.append(label_name)
    plt.legend(plt_handlers, plt_titles, loc='lower right', framealpha=.5)

    f = io.BytesIO()
    plt.savefig(f, bbox_inches='tight', pad_inches=0)
    plt.cla()
    plt.close()

    out_size = (img.shape[1], img.shape[0])
    out = PIL.Image.open(f).resize(out_size, PIL.Image.BILINEAR).convert('RGB')
    out = np.asarray(out)
    return out


# -----------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('labels_file')
    parser.add_argument('in_dir')
    parser.add_argument('out_dir')
    args = parser.parse_args()

    if osp.exists(args.out_dir):
        print('Output directory already exists:', args.out_dir)
        quit(1)
    os.makedirs(args.out_dir)
    os.makedirs(osp.join(args.out_dir, 'JPEGImages'))
    os.makedirs(osp.join(args.out_dir, 'SegmentationClass'))
    os.makedirs(osp.join(args.out_dir, 'SegmentationClassVisualization'))
    print('Creating dataset:', args.out_dir)

    class_names = []
    class_name_to_id = {}
    for i, line in enumerate(open(args.labels_file).readlines()):
        class_id = i - 1  # starts with -1
        class_name = line.strip()
        class_name_to_id[class_name] = class_id
        if class_id == -1:
            assert class_name == '__ignore__'
            continue
        elif class_id == 0:
            assert class_name == '_background_'
        class_names.append(class_name)
    class_names = tuple(class_names)
    print('class_names:', class_names)
    out_class_names_file = osp.join(args.out_dir, 'class_names.txt')
    with open(out_class_names_file, 'w') as f:
        f.writelines('\n'.join(class_names))
    print('Saved class_names:', out_class_names_file)

    colormap = labelme.utils.label_colormap(255)

    for label_file in glob.glob(osp.join(args.in_dir, '*.json')):
        print('Generating dataset from:', label_file)
        with open(label_file) as f:
            base = osp.splitext(osp.basename(label_file))[0]
            out_img_file = osp.join(
                args.out_dir, 'JPEGImages', base + '.jpg')
            out_lbl_file = osp.join(
                args.out_dir, 'SegmentationClass', base + '.png')
            out_viz_file = osp.join(
                args.out_dir, 'SegmentationClassVisualization', base + '.jpg')

            data = json.load(f)

            img_file = osp.join(osp.dirname(label_file), data['imagePath'])
            img = skimage.io.imread(img_file)
            skimage.io.imsave(out_img_file, img)

            lbl = labelme_shapes_to_label(
                img_shape=img.shape,
                shapes=data['shapes'],
                label_name_to_value=class_name_to_id,
            )
            lbl_pil = PIL.Image.fromarray(lbl)
            # Only works with uint8 label
            # lbl_pil = PIL.Image.fromarray(lbl, mode='P')
            # lbl_pil.putpalette((colormap * 255).flatten())
            lbl_pil.save(out_lbl_file)

            viz = draw_label(
                lbl, img, class_names, colormap=colormap)
            skimage.io.imsave(out_viz_file, viz)


if __name__ == '__main__':
    main()
