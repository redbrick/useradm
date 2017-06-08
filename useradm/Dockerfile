FROM python:3-alpine
WORKDIR /usr/src/app
ADD . /usr/src/app
RUN  apk add --no-cache openldap-dev cyrus-sasl-dev build-base && \
     pip install -r requirements.txt
CMD [ "python", "useradm.py" ]
