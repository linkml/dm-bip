# Building the Pipeline Docker Image
To build the Docker image, run:

```
docker build -t dm-bip-env .
```

# Start the Container
The image's default command is:

```
poetry run dm-bip run
```

To start the container and run the default command:
```
docker run --rm dm-bip-env
```

You should see "Hello, World!" printed in the output.

# Run Other Commands
If you want to run additional commands inside the container, append them after the image name. For example:

```
docker run --rm -it dm-bip-env make test
```

```
docker run --rm -it dm-bip-env make lint
```


