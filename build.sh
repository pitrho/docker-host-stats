#!/bin/bash

IMAGE_TAG="pitrho/docker-host-stats"

# Custom die function.
#
die() { echo >&2 -e "\nRUN ERROR: $@\n"; exit 1; }

# Parse the command line flags.
#
while getopts "" opt; do
  case $opt in
    \?)
      die "Invalid option: -$OPTARG"
      ;;
  esac
done

# Crete the build directory
rm -rf build
mkdir build

cp reporter.sh build/

# Copy docker file tmpl to build Dir. Currently not doing anything to the
# template, just keeping for convention
cp Dockerfile.tmpl build/Dockerfile

# Build image
docker build -t="${IMAGE_TAG}" build/

# Clean up build directory
rm -rf build
