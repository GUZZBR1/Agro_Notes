#!/bin/bash
set -e

###
# This entrypoint script will check to see if certain directories are empty
# (as is the case when a directory is bind-mounted from the host), and will
# populate them from the pre-built farmOS codebase in the image.
###

# If the Drupal directory is empty, populate it from pre-built files.
if [ -d ${DRUPAL_PATH} ] && ! [ "$(ls -A ${DRUPAL_PATH}/)" ]; then
  if [ -w "${DRUPAL_PATH}" ]; then
    echo "farmOS codebase not detected. Copying from pre-built files in the Docker image."
    cp -rp ${BUILD_PATH}/. ${DRUPAL_PATH}
  else
    echo "Error initializing ${DRUPAL_PATH}. The directory must be writable by $(whoami) (user ID $(id -u)) inside the container."
    exit 1
  fi
fi

# If the sites directory is empty, populate it from pre-built files.
if [ -d ${DRUPAL_PATH}/web/sites ] && ! [ "$(ls -A ${DRUPAL_PATH}/web/sites/)" ]; then
  if [ -w "${DRUPAL_PATH}/web/sites" ]; then
    echo "farmOS sites directory is empty. Copying from pre-built files in the Docker image."
    cp -rp ${BUILD_PATH}/web/sites/. ${DRUPAL_PATH}/web/sites
  else
    echo "Error initializing ${DRUPAL_PATH}/web/sites. The directory must be writable by $(whoami) (user ID $(id -u)) inside the container."
    exit 1
  fi
fi

if [ -n "$FARMOS_FS_READY_SENTINEL_FILENAME" ]; then
  echo "ready" > "$FARMOS_FS_READY_SENTINEL_FILENAME"
fi

# Execute the arguments passed into this script.
echo "Attempting: $@"
exec "$@"
