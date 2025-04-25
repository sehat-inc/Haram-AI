# start from python base image
FROM python:3.12

# change working directory
WORKDIR /code

# add requirements file to image
COPY ./requirements.txt /code/requirements.txt

# install python libraries
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# add python code
COPY ./backend/ /code/backend/

# specify default commands
CMD ["fastapi", "run", "backend/api.py", "--port", "80"]