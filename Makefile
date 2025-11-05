# Variables
REGISTRY = calbuco:5000/thorium
IMAGE = net-mon
GIT_COMMIT := $(shell git rev-parse --short HEAD)
TAG = latest

# Target to export dependencies and build the Docker image
build:
	poetry self add poetry-plugin-export
	poetry export --without-hashes --output requirements.txt
	docker build -t $(REGISTRY)/$(IMAGE):latest .
	docker tag $(REGISTRY)/$(IMAGE):latest $(REGISTRY)/$(IMAGE):$(GIT_COMMIT)

docker_push:
	docker push $(REGISTRY)/$(IMAGE):$(GIT_COMMIT)
	docker push $(REGISTRY)/$(IMAGE):latest

# Target to run tests using poetry and pytest
test:
	poetry run pytest
