# Start from the base node:alpine image
FROM node:alpine

# Create a separate directory for node_modules
RUN mkdir /home/node_modules

# Set the working directory to the app directory in the Docker container
WORKDIR /home/app/mapf/dev

# Copy package.json and package-lock.json
COPY ./dev/env_visualizer/package*.json /home/node_modules/

# Install all npm dependencies in the new directory
RUN cd /home/node_modules && npm install

# Set the NODE_PATH environment variable
ENV NODE_PATH=/home/node_modules/node_modules

# The command that will be run when the Docker container starts
CMD [ "node", "env_visualizer/" ]
