FROM public.ecr.aws/lambda/python:3.12

WORKDIR /app

ARG DEBIAN_FRONTEND=noninteractive

RUN microdnf update -y
RUN microdnf update -y python3 curl libcom_err ncurses expat libblkid libuuid 
RUN microdnf install python3-pip git gcc make cmake g++ mesa-libGL -y

RUN pip3 install fastapi
RUN pip3 install mangum

COPY ./api.requirements.txt ./api.requirements.txt

RUN pip3 install -r api.requirements.txt --target "${LAMBDA_TASK_ROOT}"

COPY . ${LAMBDA_TASK_ROOT}

CMD [ "api.handler" ]