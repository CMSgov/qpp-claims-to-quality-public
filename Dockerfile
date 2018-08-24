FROM bayesimpact/teradata-connector:latest

RUN chown -R root /home/tduser/
WORKDIR /home/tduser/

RUN yum makecache fast
RUN yum update -y && yum clean all
RUN yum install -y openssh-clients wget gcc make

RUN mkdir ./analyzer
WORKDIR /home/tduser/analyzer

# Install supervisord - needs python2.7.
RUN pip install supervisor
RUN mkdir /var/log/supervisord/

COPY bin/ bin/

COPY requirements.txt .
# Set locale (required for ciso8601) and install requirements.
RUN LC_ALL='en_US.UTF-8' pip3.6 install -r requirements.txt --no-cache-dir

# Use 'bash -c' as entrypoint.
ENTRYPOINT ["/bin/bash", "-c"]
