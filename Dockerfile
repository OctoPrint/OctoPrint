FROM python:2.7.12
EXPOSE 5000
VOLUME /user/octoprint/.octoprint

WORKDIR /opt/octoprint

#install ffmpeg
RUN  wget -O ffmpeg.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-32bit-static.tar.xz \
	&& mkdir -p /opt/ffmpeg \
	&& tar xvf ffmpeg.tar.xz -C /opt/ffmpeg --strip-components=1

#Copy repo to /opt/octoprint
ADD ./ /opt/octoprint/

#Perform installation
RUN virtualenv venv \
	&& ./venv/bin/python setup.py install

#Create an octoprint user
RUN useradd -ms /bin/bash octoprint
USER octoprint

CMD ["/opt/octoprint/venv/bin/octoprint"]
