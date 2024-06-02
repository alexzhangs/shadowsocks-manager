#
# This Dockerfile is used to build a Docker image for the Shadowsocks Manager.
# It sets up the necessary dependencies and configurations for running the Shadowsocks Manager.
#
# Volume:
#   - /var/local/ssm: Data home directory for shadowsocks-manager in the container.
#
# Environment:
#   The following environment variables are exported in the Dockerfile:
#
#   - SSM_USER:         The user name for running the shadowsocks-manager. 
#   - SSM_DATA_HOME:    The data home directory for shadowsocks-manager in the container.
#   - SSM_ENV:          Expose environment variables to supervisord.
#
# Expose:
#   - 80: The port for the shadowsocks-manager web interface.
#   - 443: The port for the shadowsocks-manager web interface.
#
# Build:
#   $ docker build -t alexzhangs/shadowsocks-manager ../..
#
# Run:
#   # for development environment
#   $ docker run -d -p 80 alexzhangs/shadowsocks-manager
#
#   # for production environment
#   $ docker run -d -p 80 -v /path/on/your/host:/var/local/ssm alexzhangs/shadowsocks-manager \
#                -e SSM_SECRET_KEY=yourkey -e SSM_DEBUG=False -u admin -p yourpassword -M admin@yourdomain.com
#
# For more information, please refer to the project repository:
#   https://github.com/alexzhangs/shadowsocks-manager
#
FROM python:3.12-alpine

ENV DIST alpine

# To enable proxy at build time, use:
# docker build --build-arg https_proxy=http://host.docker.internal:$PROXY_HTTP_PORT_ON_HOST ...
ARG http_proxy https_proxy all_proxy

# Install supervisor nginx
RUN apk --no-cache add supervisor nginx \
        # temporarily used by git+https://github.com/alexforks/django-admin-lazy-load
        git \
        # used by uwsgi
        gcc linux-headers libc-dev \
        # used by cffi
        libffi-dev \
        # used by docker-entrypoint.sh
        bash sudo \
        # used by acme.sh
        curl openssl && \
    # Remove the default nginx site file
    rm /etc/nginx/http.d/default.conf

# Install acme.sh
RUN curl -sL https://get.acme.sh | sh

# Set the PATH for acme.sh
ENV PATH=$PATH:/root/.acme.sh

# Verify that acme.sh is installed
RUN acme.sh --version

# Set environment variables
ENV SSM_USER=ssm
ENV SSM_DATA_HOME=/var/local/ssm
ENV SSM_ENV=SSM_DATA_HOME=$SSM_DATA_HOME

# Create user
RUN adduser -D "${SSM_USER}"

# Set work directory
WORKDIR /shadowsocks-manager

# Copy the current directory contents at local into the container
COPY . .

# Copy supervisor config file
COPY deploy/supervisor/vendors/* /etc/supervisor.d/

# Rename /etc/supervisor.d/*.conf to /etc/supervisor.d/*.ini
RUN for file in /etc/supervisor.d/*.conf; do mv $file ${file%.*}.ini; done

# Copy nginx config file
COPY deploy/nginx /etc/nginx/
RUN ln -s ../sites-enabled/ssm.conf /etc/nginx/http.d/ssm.conf

RUN chmod +x docker/*.sh

# Set VOLUME
RUN mkdir -p "${SSM_DATA_HOME}"
VOLUME [ "${SSM_DATA_HOME}" ]

# Install shadowsocks-manager
RUN pip install --no-cache-dir -e . && chown -R ${SSM_USER}:${SSM_USER} .

# Expose the nginx port
EXPOSE 80 443

# Start supervisord
ENTRYPOINT [ "./docker/docker-entrypoint.sh" ]