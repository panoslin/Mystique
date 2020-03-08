#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by panos on 12/31/19
# IDE: PyCharm

import ffmpeg
import jmespath
from math import ceil

# vprofile = [
#     "baseline",
#     "main",
#     "high",
#     "high10",
#     "high422",
#     "high444"
# ]

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


def cal_macroblocks_per_sec(width, height, frame_rate):
    return ceil(width / 16.0) * ceil(height / 16.0) * frame_rate


def gen_level(macroblocks_per_sec):
    for level, max_decoding_speed_in_macroblocks_per_sec in level2macroblocks_per_sec.items():
        if macroblocks_per_sec <= max_decoding_speed_in_macroblocks_per_sec:
            return level


def level_generator(input_file):
    meta = ffmpeg.probe(filename=input_file)
    # vprofile = jmespath.search("streams[0].profile", meta)
    width, height, avg_frame_rate = jmespath.search("streams[?codec_type=='video'].[width, height, avg_frame_rate][0]", meta)
    macroblocks_per_sec = cal_macroblocks_per_sec(width=width, height=height, frame_rate=eval(avg_frame_rate))
    level = gen_level(macroblocks_per_sec=macroblocks_per_sec)
    return level, macroblocks_per_sec


if __name__ == '__main__':
    res = level_generator("example.mp4")
    print(res)
