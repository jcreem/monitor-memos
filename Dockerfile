# pull official base image
FROM  ubuntu:20.04

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
# install dependencies
RUN apt-get update &&\
    DEBIAN_FRONTEND=noninteractive\
    apt-get upgrade -y &&\
    apt-get install -y build-essential git python3 python3-pip
    
#RUN git clone https://github.com/zeus-one/memo.cash-notifier
COPY requirements.txt .
COPY monitor_memos.py .
RUN pip3 install -r requirements.txt
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
CMD ["python3", "monitor_memos.py",  "1rmJL9oWekn5r6iCS8XHzPDh6xTgH542e"] 
