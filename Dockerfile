FROM python:2.7.12
EXPOSE 5000
VOLUME /root/.octoprint

RUN  wget -O ffmpeg.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-32bit-static.tar.xz && mkdir -p /opt/ffmpeg && tar xvf ffmpeg.tar.xz -C /opt/ffmpeg --strip-components=1

ADD ./ /opt/octoprint/
RUN cd /opt/octoprint && python setup.py install

CMD ["octoprint", "--iknowwhatimdoing"]
