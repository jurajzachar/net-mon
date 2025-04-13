# Variables
IMAGE_NAME = net-mon
TAG = latest

# Target to export dependencies and build the Docker image
build:
	poetry export --without-hashes --output requirements.txt
	docker build -t $(IMAGE_NAME):$(TAG) .

# Target to run tests using poetry and pytest
test:
	poetry run pytest