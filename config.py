#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by panos on 2020/3/8
# IDE: PyCharm


server = {
        "max_avaliable_transcoding_resolution": "4k"
}

resolution = {
    ## resolution_tag: {width, height}
    '240': {'long': 428, 'short': 240},
    '360': {'long': 640, 'short': 360},
    'sd': {'long': 848, 'short': 480},
    'xga': {'long': 1024, 'short': 576},
    'hd': {'long': 1280, 'short': 720},
    'fullhd': {'long': 1920, 'short': 1080},
    '2k': {'long': 2560, 'short': 1440},
    '4k': {'long': 3840, 'short': 2160},
    '5k': {'long': 5120, 'short': 2880},
    '8k': {'long': 7680, 'short': 4320},
    '8k+': {'long': 10240, 'short': 4320}
}

level2macroblocks_per_sec = {'1': 1485,
                             '2': 11880,
                             '2.1': 19800,
                             '3': 40500,
                             '3.1': 108000,
                             # '4': 245760,
                             '4.1': 245760,
                             '5': 589824,
                             '5.1': 983040,
                             '5.2': 2073600,
                             '6': 4177920,
                             '6.1': 8355840,
                             '6.2': 16711680
                             }