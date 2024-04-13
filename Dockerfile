#
# This Dockerfile is used to build a Docker image for the Shadowsocks Manager.
# It sets up the necessary dependencies and configurations for running the Shadowsocks Manager.
#
# Volume:
#   - /var/local/ssm: Data home directory for shadowsocks-manager in the container.
#
# Environment:
#   Export the following environment variables to configure the shadowsocks-manager:
#
#   - SSM_USER:         The user name for running the shadowsocks-manager. 
#   - SSM_DATA_HOME:    The data home directory for shadowsocks-manager in the container.
#
# Expose:
#   - 80: The port for the shadowsocks-manager web interface.
#
# Build:
#   $ docker build -t shadowsocks-manager .
#
# Run:
#   # for development environment
#   $ docker run -d -p 80 shadowsocks-manager
#
#   # for production environment
#   $ docker run -d -p 80 -v /path/on/your/host:/var/local/ssm shadowsocks-manager \
#                -e SSM_SECRET_KEY=yourkey -e SSM_DEBUG=False -u admin -p yourpassword -M admin@yourdomain.com
#
# For more information, please refer to the project repository:
#   https://github.com/alexzhangs/shadowsocks-manager
#
# Maintainer: Alex Zhang <alexzhangs@gamil.com>
#
# Version: 1.0
# 
FROM python:3.12

# Set environment variables
ENV SSM_USER=ssm
ENV SSM_DATA_HOME=/var/local/ssm

# Create user
RUN useradd -m "${SSM_USER}"

# Set work directory
WORKDIR /shadowsocks-manager

# Copy the current directory contents at local into the container
COPY . .

RUN chmod +x docker-entrypoint.sh

# Install shadowsocks-manager
RUN pip install -e . && chown -R ${SSM_USER}:${SSM_USER} .

# Set VOLUME
RUN mkdir -p "${SSM_DATA_HOME}"
VOLUME [ "${SSM_DATA_HOME}" ]

# Install supervisor
RUN apt-get update && apt-get install -y supervisor

# Copy supervisor config file
COPY deploy/supervisor/vendors/* /etc/supervisor/conf.d/

# Install nginx
RUN apt-get install -y nginx

# Copy nginx config file
COPY deploy/nginx/conf.d/* /etc/nginx/sites-available/

# Link the nginx config file
RUN ln -s /etc/nginx/sites-available/shadowsocks-manager.conf /etc/nginx/sites-enabled/

# Remove the default nginx config file
RUN rm /etc/nginx/sites-enabled/default

# Install sudo, used by docker-entrypoint.sh
RUN apt-get install -y sudo

# Expose the nginx port
EXPOSE 80

# Start supervisord
ENTRYPOINT [ "./docker-entrypoint.sh" ]