FROM python:3.9

RUN apt -qq update && apt -qq install -y git wget ffmpeg
 
COPY . . 

RUN pip3 install -r requirements.txt 

CMD ["bash","run.sh"]