#!/usr/bin/python

# This work is licensed under the Creative Commons Attribution 3.0 United
# States License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by/3.0/us/ or send a letter to Creative
# Commons, 171 Second Street, Suite 300, San Francisco, California, 94105, USA.

# from http://oranlooney.com/make-css-sprites-python-image-library/
# Orignial Author Oran Looney <olooney@gmail.com>

# mods by Josh Gourneau <josh@gourneau.com> to make one big horizontal sprite JPG with no spaces between images

from PIL import Image
import glob
import ffmpeg
import jmespath
import math


def generate(icon_map_path, sprite_path="sprite.jpg"):
    iconMap = sorted(glob.glob(f"{icon_map_path}/*"), key=lambda x: int(x.split("-")[-1].split(".")[0]))
    image_width, image_height = jmespath.search(
        "streams[?codec_type=='video'].[width, height][0]",
        ffmpeg.probe(iconMap[0])
    )
    total_count = len(iconMap)
    if total_count >= 10:
        master_width = image_width * 10
        master_height = image_height * math.ceil(total_count/10)
    else:
        master_width = image_width * total_count
        master_height = image_height

    master = Image.new(
        mode='RGBA',
        size=(master_width, master_height),
        color=(0, 0, 0, 0))  # fully transparent

    for count, filename in enumerate(iconMap):
        image = Image.open(filename)
        column = count % 10
        row = count // 10

        master.paste(image, (column * image_width, row * image_height))
    master.convert('RGB').save(sprite_path, transparency=0)


if __name__ == "__main__":
    from mystique.ffmpeg.transcoding import select_i_frame
    import os
    icon_map_path_ = "sprite_example"
    os.makedirs(icon_map_path_, exist_ok=True)
    select_i_frame(
        input_file="example.mp4",
        output_dir=icon_map_path_,
    )
    generate(icon_map_path=icon_map_path_, sprite_path=os.path.join(icon_map_path_, "sprite.jpg"))
