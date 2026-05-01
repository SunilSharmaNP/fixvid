FROM mysterysd/wzmlx:v3
WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app
COPY requirements.txt .
RUN pip3 install --no-cache-dir --ignore-installed -r requirements.txt --break-system-packages
COPY . .
CMD ["bash", "start.sh"]
