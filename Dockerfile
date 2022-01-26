# base image
FROM thinkwhere/gdal-python
# setup environment variable
ENV DockerHOME=/home/app/webapp
# set work directory
RUN mkdir -p $DockerHOME
# where code lives
WORKDIR $DockerHOME
# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# install dependencies
COPY . $DockerHOME
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
# port where the Django app runs
EXPOSE 8000
# start server
CMD python manage.py runserver