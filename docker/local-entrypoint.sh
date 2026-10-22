#!/bin/sh
set -eu

drupal_path=${DRUPAL_PATH:-/opt/drupal}
profile_path=${FARMOS_PROFILE_PATH:-/opt/farm-profile}
build_path=${BUILD_PATH:-/var/farmOS}

# Populate the bind-mounted Drupal directory before overlaying this worktree's
# farmOS profile. Mounting the profile inside /opt/drupal before initialization
# would make an otherwise empty code volume appear initialized.
if [ ! -x "$drupal_path/vendor/bin/drush" ]; then
  cp -rp "$build_path"/. "$drupal_path"/
fi

mkdir -p "$drupal_path/web/profiles/farm"
find "$drupal_path/web/profiles/farm" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
tar --exclude=.git --exclude=.omx --exclude=docker/local -C "$profile_path" -cf - . \
  | tar -C "$drupal_path/web/profiles/farm" -xf -

exec /usr/local/bin/docker-entrypoint.sh "$@"
