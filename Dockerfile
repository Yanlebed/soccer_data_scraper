# Stage 1: Build stage using an image with yum available
FROM amazonlinux:2 AS builder

# Install required dependencies in the builder stage
RUN yum update -y && yum install -y \
    libX11 \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXi \
    libXtst \
    cups-libs \
    dbus-glib \
    xorg-x11-server-Xvfb

# Stage 2: Final Lambda image
FROM public.ecr.aws/lambda/python:3.12

# Copy your application code
COPY lambda_functions/ ${LAMBDA_TASK_ROOT}/lambda_functions/
COPY models/ ${LAMBDA_TASK_ROOT}/models/
COPY scraper/ ${LAMBDA_TASK_ROOT}/scraper/
COPY storage/ ${LAMBDA_TASK_ROOT}/storage/
COPY utils/ ${LAMBDA_TASK_ROOT}/utils/
COPY config_totalcorner.py ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
RUN pip install --no-cache-dir playwright gspread google-auth gspread-dataframe pandas boto3

# Install the Chromium browser for Playwright (without --with-deps)
RUN python -m playwright install chromium

# Set the Lambda handler
CMD [ "lambda_functions/schedule_updater.lambda_handler" ]
