#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by panos on 12/31/19
# IDE: PyCharm

import ffmpeg
import jmespath

avaliable_resoulution = {
    12: '240',
    # 11: 'org',
    11: '360',
    10: 'sd',
    9: 'xga',
    8: 'hd',
    7: 'fullhd',
    6: '2k',
    5: '4k',
    4: '5k',
    3: '8k',
    2: '8k+',

}

resolution_tag2priority = {r: p for p, r in avaliable_resoulution.items()}


def cal_main_side(ratio):
    if ratio >= 16 / 9:
        # 如果这是一个超宽视频，则适配屏幕宽度
        main = 'width'
    elif 16 / 9 > ratio > 1:
        # 如果这是一个不宽的横屏视频，则适配视频高度
        main = 'height'
    elif 1 >= ratio > 9 / 16:
        # 如果这是一个不高的竖屏视频，则适配竖屏视频的宽度
        main = 'width'
    else:  ## ratio <= 9 / 16:
        # 如果这是一个很高的竖屏视频，则适配竖屏视频的高度
        main = 'height'
    return main


def cal_max_resolution(ratio, width, height):
    left, right = (width, height) if ratio >= 1 else (height, width)
    if right < 480:
        max_resolution = '360'
    elif left < 1024 and right < 576:
        max_resolution = 'sd'
    elif left < 1280 and right < 720:
        max_resolution = 'xga'
    elif left < 1920 and right < 1080:
        max_resolution = 'hd'
    elif left < 2560 and right < 1440:
        max_resolution = 'fullhd'
    elif left < 3840 and right < 2160:
        max_resolution = '2k'
    else:  ## left < 5120 and right < 2880:
        max_resolution = '4k'
    # elif left < 7680 and right < 4320:
    #     max_resolution = '5k'
    # elif left < 10240 and right <= 4320:
    #     max_resolution = '8k'
    # else:
    #     max_resolution = '8k+'

    return max_resolution


def resolution_tag2resolution(resolution_tag):  ## without org
    # 获取转码目标的最大容许尺寸
    if resolution_tag == '8k':
        width = 7680
        height = 4320
    elif resolution_tag == '5k':
        width = 5120
        height = 2880
    elif resolution_tag == '4k':
        width = 3840
        height = 2160
    elif resolution_tag == '2k':
        width = 2560
        height = 1440
    elif resolution_tag == 'fullhd':
        width = 1920
        height = 1080
    elif resolution_tag == 'hd':
        width = 1280
        height = 720
    elif resolution_tag == 'xga':
        width = 1024
        height = 576
    elif resolution_tag == 'sd':
        width = 848
        height = 480
    elif resolution_tag == '360':
        width = 640
        height = 360
    elif resolution_tag == 'org':
        width = -2
        height = -2
    else:  ## res == '240':
        width = 428
        height = 240
    return width, height,


def _resolution_generator(width, height):
    width, height = int(width), int(height)
    ratio = width / height

    main_side = cal_main_side(ratio=ratio)

    max_resolution_tag = cal_max_resolution(ratio=ratio, width=width, height=height)

    max_priority = resolution_tag2priority[max_resolution_tag]

    adp_lenth = -2

    for priority, resolution_tag in avaliable_resoulution.items():
        if max_priority <= priority:
            formal_width, formal_height = resolution_tag2resolution(resolution_tag=resolution_tag)
            if ratio > 1 and main_side == 'width':
                # 横屏视频，适配横边
                resolution = f"{formal_width}:{adp_lenth}"
            elif ratio > 1 and main_side == 'height':
                # 横屏视频，适配高边
                resolution = f"{adp_lenth}:{formal_height}"
            elif ratio <= 1 and main_side == 'width':
                # 竖屏视频，适配横边
                resolution = f"{formal_height}:{adp_lenth}"
            else:  ## ratio <= 1 and main_side == 'height':
                # 竖屏视频，适配竖边
                resolution = f"{adp_lenth}:{formal_width}"

            yield resolution, priority, resolution_tag, max_priority, max_resolution_tag
    else:
        if max_priority > resolution_tag2priority["4k"]:
            yield "-2:-2", 1, "org", max_priority, max_resolution_tag


def resolution_generator(input_file):
    meta = ffmpeg.probe(filename=input_file)
    width, height = jmespath.search("streams[?codec_type=='video'].[width, height][0]", meta)
    yield from _resolution_generator(width=width, height=height)


if __name__ == '__main__':
    for ele in resolution_generator(input_file="example.mp4"):
        print(ele)
