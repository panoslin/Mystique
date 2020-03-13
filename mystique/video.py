#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Created by panos on 2020/3/8
# IDE: PyCharm

import ffmpeg
import jmespath
from math import ceil
from Mystique import config
import os
import uuid
from glob import glob
import shutil
import math
from PIL import Image


class Video:
    def __init__(self, video_path="mystique/video/example.mp4"):
        self.video_path = video_path
        if not os.path.exists(self.video_path):
            raise FileNotFoundError
        self.meta = ffmpeg.probe(filename=self.video_path)
        self.video_meta = jmespath.search("streams[?codec_type=='video']", self.meta)[0]
        self.audio_meta = jmespath.search("streams[?codec_type=='audio']", self.meta)[0]
        self.width = int(self.video_meta['width'])
        self.height = int(self.video_meta['height'])
        self.bit_rate = int(self.video_meta['bit_rate'])
        self.avg_frame_rate = self.fps = eval(self.video_meta['avg_frame_rate'])
        self.macroblocks_per_sec = ceil(self.width / 16.0) * ceil(self.height / 16.0) * self.avg_frame_rate
        self.level = self.generate_level()
        self.ratio = self.width / self.height
        self.main_side = self.cal_main_side()
        self.max_resolution = self.cal_max_resolution()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
        # print(f"exc_type, exc_val, exc_tb: {exc_type, exc_val, exc_tb}")

    def generate_level(self):
        for level, max_decoding_speed_in_macroblocks_per_sec in config.level2macroblocks_per_sec.items():
            if self.macroblocks_per_sec <= max_decoding_speed_in_macroblocks_per_sec:
                return level

    def cal_main_side(self):
        ##                ratio
        ## |________|_______|________|_______|
        ## |       9/16     1       16/9     |
        ## |<height>|<width>|<height>|<width>|
        if self.ratio >= 16 / 9:
            main = 'width'
        elif 16 / 9 > self.ratio > 1:
            main = 'height'
        elif 1 >= self.ratio > 9 / 16:
            main = 'width'
        else:  ## ratio <= 9 / 16:
            main = 'height'
        return main

    def cal_max_resolution(self):
        long, short = (self.width, self.height) if self.ratio >= 1 else (self.height, self.width)
        if long < config.resolution["sd"]['short']:
            max_resolution = "360"  ## assuming "360" is the lowest benchmark
        else:
            max_resolution = "360"  ## assuming "360" is the lowest benchmark
            for resolution_tag, resolution in config.resolution.items():
                if long >= resolution['long'] and short >= resolution['short']:
                    max_resolution = resolution_tag
        return max_resolution

    def generate_scale(self):
        """
        priority: the larger number means the more urgent
        :return:
        """
        tag2priority = {tag: len(config.resolution) - num for num, tag in enumerate(config.resolution)}
        min_priority = tag2priority[self.max_resolution]
        for resolution_tag, resolution in config.resolution.items():
            priority = tag2priority[resolution_tag]
            if priority > min_priority:
                if config.server["max_avaliable_transcoding_resolution"]:
                    if priority <= tag2priority[config.server["max_avaliable_transcoding_resolution"]]:
                        continue  ## the upper limit of the server
                formal_width, formal_height = resolution.values()
                if self.ratio > 1 and self.main_side == 'width':
                    scale = f"{formal_width}:{-2}"
                elif self.ratio > 1 and self.main_side == 'height':
                    scale = f"{-2}:{formal_height}"
                elif self.ratio <= 1 and self.main_side == 'width':
                    scale = f"{formal_height}:{-2}"
                else:  ## ratio <= 1 and main_side == 'height':
                    scale = f"{-2}:{formal_width}"
                yield scale, priority, resolution_tag, min_priority, self.max_resolution
        else:
            if config.server["max_avaliable_transcoding_resolution"]:
                priority_bound = tag2priority[config.server["max_avaliable_transcoding_resolution"]]
                ## if max_resolution is more than 4k, the server may not be able to transcode the video to org
                if priority_bound < min_priority:
                    yield "-2:-2", 1, "org", min_priority, self.max_resolution
            else:
                yield "-2:-2", 1, "org", min_priority, self.max_resolution

    def mux2container(self, output_file="muxed.mp4"):
        """
        mux-remux video container to "mp4" (or other container format)
        only modify the meta data of the video file, no decoding/encoding, hence this should be real fast
        :param output_file:
        :return:
        """
        process = (
            ffmpeg
                .input(self.video_path)
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
            self,
            output_dir="slicing",
            segment_time=10,
            segment_list="playlist.m3u8"
    ):
        ## ffmpeg -i example.mp4 -c:v h264 -flags +cgop -g 30 -hls_time 5 -hls_list_size 0 -hls_segment_filename '%03d.ts' -strftime 1 -strftime_mkdir 1 out.m3u8
        ## ffmpeg -re -i example.mp4 -codec copy -map 0 -f segment -segment_list playlist.m3u8 -segment_list_flags +live -segment_time 5 out%03d.ts
        ## -segment_format mpegts
        ext = self.video_path.split(".")[-1]
        if not output_dir:
            output_dir = os.path.join(
                os.path.abspath(
                    os.path.dirname(self.video_path)
                ),
                uuid.uuid1().hex
            )
        else:
            output_dir = output_dir.rstrip("/\\")
        os.makedirs(output_dir, exist_ok=True)
        file_name = os.path.join(output_dir, f"%03d.{ext}")
        process = (
            ffmpeg
                .input(self.video_path)
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

    def slice2hls(
            self,
            hls_time=5,
            segment_list="hls.m3u8",
            hls_base_url="",
            hls_segment_filename='%Y/%m/%d/%%04d.ts',
    ):
        ## ffmpeg -i example.mp4 -flags +cgop -g 30 -hls_time 5 -hls_list_size 0 -hls_allow_cache 1 -hls_base_url '' -strftime 1 -hls_segment_filename '%Y/%m/%d/%03d.ts' -strftime_mkdir 1 -hls_segment_type 'mpegts' out.m3u8
        ## ffmpeg -i example.mp4 -c copy -hls_allow_cache 1 -hls_flags second_level_segment_index -hls_segment_filename '%Y/%m/%d/%%04d.ts' -hls_segment_type "mpegts" -hls_time 10 -strftime_mkdir 1 -strftime 1 -hls_list_size 0 -f hls hls.m3u8
        print("breakdown")
        process = (
            ffmpeg
                .input(self.video_path)
                .output(
                filename=segment_list,
                hls_segment_filename=hls_segment_filename,
                hls_flags="second_level_segment_index+iframes_only+independent_segments",
                start_number=0,
                loglevel="fatal",
                hls_time=hls_time,
                hls_allow_cache=1,
                hls_base_url=hls_base_url,
                strftime=1,
                hls_list_size=0,
                strftime_mkdir=1,
                hls_segment_type='mpegts',
                hls_playlist_type='vod',
                # force_key_frames='expr:gte(t,n_forced*2)', ## a key frame will be present every 2 seconds
                r=self.fps, ## fixed frame rate
                g=self.fps * 2,  ## twice of fps, meaning that a key frame will be present every 2 seconds
                keyint_min=self.fps * 2,  ## twice of fps, meaning that a key frame will be present every 2 seconds
                sc_threshold=0,
                c="copy",
                format="hls",
            )
                .run_async(
                pipe_stdout=True,
                pipe_stderr=True,
                overwrite_output=True
            )
        )
        stdout, stderr = process.communicate()
        return stdout.decode(), stderr.decode()

    def transcode2mp4(self, scale, level="3.1", output_file="transcoded.mp4", vcodec="libx264"):
        """
        decoding/encoding the input_file to output_file with the specific arguments
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
                .input(self.video_path)
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

    @classmethod
    def concat(cls, input_file, output_file="concated.mp4", remove=False):
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

    def select_i_frame(self, output_dir="iframe"):
        """
        output the i-frame of a video
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
                self.video_path,
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

    def select_p_frame_b4_i_frame(self, output_dir="pframe", n=1):
        """
        output the p_frame before i_frame of a video
        :param output_dir=None,
        :param n: select the last n frame before i-frame
        :return: stdout, stderr
        """
        ## ffprobe -i example.mp4 -v quiet -select_streams v -show_entries frame=pkt_pts_time,pict_type
        ## ffmpeg -ss 1.835167 -i example.mp4 -vframes 1 0.jpg
        os.makedirs(output_dir, exist_ok=True)
        frames = ffmpeg.probe(
            self.video_path,
            select_streams="v",
            show_entries="frame=pkt_pts_time,pict_type")["frames"]
        count = 1
        process = lambda x, ss: (
            ffmpeg
                .input(self.video_path, ss=ss)
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
                    pass
                else:
                    count += 1
        else:
            stdout, stderr = process(f"{output_dir}/core-{count}.jpg", frames[-1]["pkt_pts_time"]).communicate()
            if stderr:
                pass

        return True

    def select_frame_by_time_interval(self, output_dir="interval", interval=1):
        """
        output the p_frame before i_frame of a video
        :param output_dir=None,
        :param interval=1,
        :return: stdout, stderr
        """
        ## ffmpeg -i vid.avi -f image2 -vf fps=fps=1 foo-%03d.jpeg
        os.makedirs(output_dir, exist_ok=True)
        process = (
            ffmpeg
                .input(
                self.video_path,
            )
                .output(
                f"{output_dir}/core-%08d.jpg",
                vf=f"fps=fps={interval}",
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

    @classmethod
    def sprite(cls, icon_map_path, sprite_path="sprite.jpg"):
        iconMap = sorted(glob(f"{icon_map_path}/*"), key=lambda x: int(x.split("-")[-1].split(".")[0]))
        image_width, image_height = jmespath.search(
            "streams[?codec_type=='video'].[width, height][0]",
            ffmpeg.probe(iconMap[0])
        )
        total_count = len(iconMap)
        if total_count >= 10:
            master_width = image_width * 10
            master_height = image_height * math.ceil(total_count / 10)
        else:
            master_width = image_width * total_count
            master_height = image_height

        master = Image.new(
            mode='RGBA',
            size=(master_width, master_height),
            color=(0, 0, 0, 0))  # fully transparent
        max_column = 0
        max_row = 0
        for count, filename in enumerate(iconMap):
            image = Image.open(filename)
            column = count % 10
            max_column = column if column > max_column else max_column
            row = count // 10
            max_row = row if row > max_row else row

            master.paste(image, (column * image_width, row * image_height))
        master.convert('RGB').save(sprite_path, transparency=0)
        return total_count, max_column + 1, max_row + 1


if __name__ == "__main__":
# video = Video(video_path="example.mp4")

# a = video.cal_max_resolution()
# print(a)

# for ele in video.generate_scale():
#     print(ele)

# res = video.select_frame_by_time_interval()

    with Video(video_path="example.mp4") as video:
        # video.select_i_frame()
        video.slice2hls(
            hls_time=1,
            segment_list="hls.m3u8",
            hls_base_url='',
            # hls_segment_filename='%%03d.ts',
        )
