FROM python:3
WORKDIR /srv
COPY . .
RUN pip3 install pyyaml datetime art requests\
  && apt-get update \
  && apt-get install rsync -y \
  && chmod +x bkup-script.py
ENTRYPOINT ["python3","-u", "bkup-script.py"]
