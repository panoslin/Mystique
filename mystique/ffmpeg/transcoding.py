#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by panos on 2019/12/22
# IDE: PyCharm

import ffmpeg
import os
import uuid
from glob import glob
import jmespath
import traceback
from pprint import pprint
import shutil

def probe_codex(file_path):
    probe = ffmpeg.probe(file_path)
    codec = jmespath.search("streams[*].codec_name", probe)
    return codec


def mux2container(input_file, output_file="out.mp4"):
    """
    mux-remux video container to "mp4" (or other container format)
    only modify the meta data of the video file, no decoding/encoding, hence this should be real fast
    :param input_file:
    :param output_file:
    :return:
    """
    process = (
        ffmpeg
            .input(input_file)
            .output(
            filename=output_file,
            loglevel="fatal",
            strict="-2",
            vcodec="copy",
            acodec="copy"
        )
            .run_async(pipe_stdout=True, pipe_stderr=True)
    )
    stdout, stderr = process.communicate()
    return stdout.decode(), stderr.decode()


def slice2segment(
        input_file,
        output_dir=None,
        segment_time=10,
        segment_list="playlist.m3u8"
):
    ## ffmpeg -i example.mp4 -c:v h264 -flags +cgop -g 30 -hls_time 5 -hls_list_size 0 -hls_segment_filename '%03d.ts' -strftime 1 -strftime_mkdir 1 out.m3u8
    ## ffmpeg -re -i example.mp4 -codec copy -map 0 -f segment -segment_list playlist.m3u8 -segment_list_flags +live -segment_time 5 out%03d.ts
    ## -segment_format mpegts
    ext = input_file.split(".")[-1]
    if not output_dir:
        output_dir = os.path.join(
            os.path.abspath(
                os.path.dirname(input_file)
            ),
            uuid.uuid1().hex
        )
    else:
        output_dir = output_dir.rstrip("/\\")
    os.makedirs(output_dir, exist_ok=True)
    file_name = os.path.join(output_dir, f"%03d.{ext}")
    process = (
        ffmpeg
            .input(input_file)
            .output(
            filename=file_name,
            loglevel="fatal",
            c="copy",
            map="0",
            format="segment",
            segment_list=os.path.join(output_dir, segment_list),
            segment_time=segment_time
        )
            .run_async(
            pipe_stdout=True,
            pipe_stderr=True,
            overwrite_output=True
        )
    )
    stdout, stderr = process.communicate()
    segments = glob(os.path.join(output_dir, f"*.{ext}"))
    m3u8 = os.path.join(output_dir, segment_list)
    return stdout.decode(), stderr.decode(), segments, m3u8


def transcode2mp4(input_file, scale, level="3.1", output_file="out.mp4", vcodec="libx264"):
    """
    decoding/encoding the input_file to output_file with the specific arguments
    :param input_file: video file path
    :param scale: target resolution in the format of "-2:720".
                  negative number representing this side will be adjusted according the other side
    :param level: reference to the table in /mystique/ffmpeg/h264-level-table.png
    :param output_file: output file path
    :param vcodec: "libx264"/"libx265" or other video codec.
                   your ffmpeg should have compiled with the specific codec
    :return:
    """
    ##  ffmpeg -i 11.mp4 -s 1280x720 -codec:v libx264 -codec:a mp3 out.mp4
    process = (
        ffmpeg
            .input(input_file)
            .output(
            filename=output_file,
            loglevel="fatal",
            # s=resolution,
            vf=f"scale={scale}",  ## "-2:720"
            vcodec=vcodec,
            # vprofile=vprofile,  ## reference to the table in /mystique/ffmpeg/h264-vprofile-table.png
            level=level,
            acodec="aac",
            movflags="faststart",  ## mv the metadata of the video to the head of the container
        )
            .run_async(
            pipe_stdout=True,
            pipe_stderr=True,
            overwrite_output=True
        )
    )
    stdout, stderr = process.communicate()
    return stdout.decode(), stderr.decode()


def concat(input_file, output_file="full.mp4", remove=False):
    """
    concat the videos
    :param input_file: 'filelist.txt'
    :param output_file: 'full.mp4'
    :param remove: remove the origin files or not.
    :return: stdout, stderr
    """
    process = (
        ffmpeg
            .input(
            input_file,
            format='concat',
            safe=0
        )
            .output(
            output_file,  ## 'full.mp4'
            loglevel="fatal",
            c='copy',
        )
            .run_async(
            pipe_stdout=True,
            pipe_stderr=True,
            overwrite_output=True
        )
    )
    stdout, stderr = process.communicate()

    if remove and not stderr:
        shutil.rmtree(os.path.dirname(input_file), ignore_errors=True)
    return stdout.decode(), stderr.decode()


def select_i_frame(input_file, output_dir="test"):
    """
    output the i-frame of a video
    :param input_file: 'b.mp4'
    :param output_dir=None,
    :return: stdout, stderr
    """
    ## ffmpeg -i example.mp4 -vf "select=eq(pict_type\,I)",mpdecimate  -vsync vfr -qscale:v 2 -f image2 core-%08d.jpg
    ## ffmpeg -ss 1.835167 -i example.mp4 -vframes 1 0.jpg
    ## ffprobe -i example.mp4 -v quiet -select_streams v -show_entries frame=pkt_pts_time,pict_type
    os.makedirs(output_dir, exist_ok=True)
    process = (
        ffmpeg
            .input(
            input_file,
        )
            .output(
            f"{output_dir}/core-%08d.jpg",
            vf='select=eq(pict_type\,I),mpdecimate',
            vsync="vfr",
            qscale="2",
            loglevel="fatal",
            f="image2",
        )
            .run_async(
            pipe_stdout=True,
            pipe_stderr=True,
            overwrite_output=True
        )
    )
    stdout, stderr = process.communicate()
    return stdout.decode(), stderr.decode()


def select_p_frame_b4_i_frame(input_file, output_dir="test", n=1):
    """
    output the p_frame before i_frame of a video
    :param input_file: 'b.mp4'
    :param output_dir=None,
    :param n: select the last n frame before i-frame
    :return: stdout, stderr
    """
    ## ffprobe -i example.mp4 -v quiet -select_streams v -show_entries frame=pkt_pts_time,pict_type
    ## ffmpeg -ss 1.835167 -i example.mp4 -vframes 1 0.jpg
    os.makedirs(output_dir, exist_ok=True)
    frames = ffmpeg.probe(input_file, select_streams="v", show_entries="frame=pkt_pts_time,pict_type")["frames"]
    count = 1
    process = lambda x, ss: (
        ffmpeg
            .input(input_file, ss=ss)
            .output(x, vframes="1", loglevel="fatal")
            .run_async(pipe_stdout=True, pipe_stderr=True, overwrite_output=True)
    )
    for num, frame in enumerate(frames):
        pict_type = frame['pict_type']
        if num > 0 and pict_type == "I":
            last_n_frame = frames[num - n]
            pkt_pts_time = last_n_frame['pkt_pts_time']
            stdout, stderr = process(f"{output_dir}/core-{count}.jpg", pkt_pts_time).communicate()
            if stderr:
                print(stderr)
            else:
                count += 1
    else:
        stdout, stderr = process(f"{output_dir}/core-{count}.jpg", frames[-1]["pkt_pts_time"]).communicate()
        if stderr:
            print(stderr)

    return True


if __name__ == '__main__':
    example_file = "example.mp4"

    # res = probe_codex(example_file)
    # pprint(res)

    # res = mux2container(input_file=example_file, output_file="mux2mkv_example.mkv")
    # pprint(res)

    # res = slice2segment(
    #     input_file=example_file,
    #     output_dir="slice2segment_example"
    #     )
    # pprint(res)

    # res = transcode2mp4(
    #     "example.mp4",
    #     output_file="265.mp4",
    #     scale="-2:-2",
    #     vcodec="libx265",
    #               )
    # pprint(res)


    # res = select_i_frame(
    #     "example.mp4",
    #     output_dir="test2",
    # )
    # pprint(res)

    # res = select_p_frame_b4_i_frame(
    #     "example.mp4",
    #     output_dir="test",
    #     n=1,
    # )
    # pprint(res)

    # res = concat(
    #     "concatlist.txt",
    #     output_file="concat_example.mp4",
    #               )
    # pprint(res)

