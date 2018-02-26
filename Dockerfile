FROM alpine:latest

RUN apk add --no-cache python3 python3-dev ca-certificates

# Copy app over
COPY . /src/

# Install app dependencies
# RUN pip3 install --upgrade pip
RUN pip3 install -r /src/requirements.txt

ENTRYPOINT ["/src/docker-entrypoint.sh"]
