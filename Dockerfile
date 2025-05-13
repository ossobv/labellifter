FROM python:3

#RUN pip install --upgrade pip
RUN apt-get -q update && \
    apt-get install -qy --no-install-recommends \
      dmtx-utils imagemagick zbar-tools && \
    apt-get clean && \
    rm -rf /var/lib/apt

# permissions and nonroot user for tightened security
#RUN adduser -D nonroot
RUN mkdir /srv/app /srv/venv && chown -R nobody:nogroup /srv
RUN mkdir -p /var/log/flask-app && touch /var/log/flask-app/flask-app.err.log && touch /var/log/flask-app/flask-app.out.log
RUN chown -R nobody:nogroup /var/log/flask-app
WORKDIR /srv/app
USER nobody

# venv
ENV VIRTUAL_ENV=/srv/venv

# python setup
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN export FLASK_APP=app.py
COPY requirements.txt .
RUN pip install -r requirements.txt

# define the port number the container should expose
#EXPOSE 5000

COPY app.py .
# CMD ["flask", "run"]
CMD ["python3", "app.py"]
