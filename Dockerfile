FROM python:2.7.12
EXPOSE 5000

ADD ./ /opt/octoprint/
RUN cd /opt/octoprint && python setup.py install

CMD ["octoprint", "--iknowwhatimdoing"]
