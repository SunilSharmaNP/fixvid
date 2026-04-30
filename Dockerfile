FROM mysterysd/wzmlx:v3

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

COPY requirements.txt .

# setuptools ও pip আপডেট করে তারপর dependencies ইনস্টল করো
RUN pip3 install --upgrade pip setuptools setuptools-scm && \
    pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]
