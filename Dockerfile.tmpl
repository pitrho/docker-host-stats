# Report (log to stdout) host statistics
#

# Use phusion/baseimage as base image.
FROM phusion/baseimage:0.9.17
MAINTAINER  pitrho

# Set up the environment
#
ENV DEBIAN_FRONTEND noninteractive

# Install build deps
#
RUN apt-get update && apt-get -y -q install \
	python \
    python-dev \
    python-distribute \
    python-pip \
	&& apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install pyCLI==2.0.3 psutil==4.2.0 requests==2.10.0 python-json-logger==0.1.5

# Copy logger script
#
COPY host-stats-logger.py /host-stats-logger.py

# Default to reporting every 30 seconds
#
ENTRYPOINT ["python", "-u", "/host-stats-logger.py"]
CMD ["-f", "30", "-cmdn"]
