FROM python:2.7.12
EXPOSE 5000

RUN git clone https://github.com/foosel/OctoPrint.git /opt/octoprint
#ADD * /opt/octoprint/
RUN cd /opt/octoprint && python setup.py install

CMD ["octoprint", "--iknowwhatimdoing"]
