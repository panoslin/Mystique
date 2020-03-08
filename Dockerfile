FROM python:3.7
##  添加国内镜像源
RUN sed -i s@/archive.ubuntu.com/@/mirrors.aliyun.com/@g /etc/apt/sources.list
RUN apt-get update -y
RUN mkdir -p /code /root/.pip/
ADD pip.conf /root/.pip/pip.conf
ADD requirements.txt /Project/
WORKDIR /Project
RUN apt-get update -y \
    && apt-get install -y ffmpeg build-essential \
    && pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
##  修复时区
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
ENV PATH=/usr/local/bin:/usr/local/sbin:/sbin:/bin:/usr/sbin:/usr/bin:/root/bin
