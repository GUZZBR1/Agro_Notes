# farmOS in Docker

**Note:** These instructions are for running farmOS on a live production server.
For local development/testing, please refer to the
[development environment](/development/environment) documentation.

## Overview

The best way to host farmOS is with [Docker](https://docker.com).

[Official farmOS Docker images](https://hub.docker.com/r/farmos/farmos) are
available on Docker Hub. These include all of farmOS's
[web server requirements](/hosting/requirements/#web-server).

This page covers how to run farmOS in Docker. Once the containers are running,
continue with the [farmOS installation steps](/hosting/install).

## Docker Run

Start by creating a directory for site data to be stored in, owned by user/group
ID `33` (`www-data` inside the Docker container).

    mkdir sites && sudo chown 33:33 sites

Use the following command to run farmOS in a Docker container (replace `x.y.z`
with the latest stable release version from the
[GitHub releases page](https://github.com/farmOS/farmOS/releases)):

    docker run --rm -p 80:80 -v "${PWD}/sites:/opt/drupal/web/sites" farmos/farmos:x.y.z

**Important**: Using the `latest` Docker tag is not recommended, because updates
require manual steps. See [Updating](/hosting/docker/#updating) below.

This will pull the farmOS Docker image, provision a farmOS web server container
listening on port 80, and bind-mount a `sites` directory into the container for
persistence of settings and uploaded files (see [Persistence](#persistence)
below).

This does not include a database or reverse proxy for SSL termination.

## Docker Compose

[Docker Compose](https://docs.docker.com/compose) can be used to encapsulate
everything in the `docker run` command above, as well as provisioning a database
and reverse proxy.

An example `docker-compose.production.yml` configuration file is provided in
the farmOS repository's `docker` directory.

Copy this to a file named `docker-compose.yml` in the directory you would like
to install farmOS in, update the `farmos/farmos:x.y.z` version reference to the
latest stable release version, and run:

    docker compose up -d

A PostgreSQL database container is included, with a hostname of `db` and default
credentials. Set a strong password and optionally change the user/database name
for added security. This database container is only provided as an example, and
can be removed if an external database is used instead.

## Persistence

All site-specific settings and user-uploaded files are stored in
`/opt/drupal/web/sites` inside the container, so it is important that the
contents of this directory be persisted outside the container. Bind-mounting a
directory from the host into the container is the recommended way to achieve
this.

The `docker run` command above does this, as well as the example
`docker-compose.production.yml` provided in the farmOS repository's `docker`
directory.

This allows a production farmOS instance to be updated simply by updating the
`farmos/farmos:x.y.z` version number and manually running database updates
(see [Updating](#updating) below). Everything outside the `sites` directory will
not be preserved and will be replaced with the new official farmOS files.

If the `sites` directory is not persisted, all settings and files will be lost
when the container is destroyed, and you will be prompted to install farmOS
again when a new container is started.

## Customizing PHP

If customizations to PHP's configuration are required, such as increasing the
maximum upload size limit, you can bind-mount a custom PHP settings file into
the container.

Create a file called `php.ini` alongside `docker-compose.yml`:

```
upload_max_filesize = 50M
post_max_size = 50M
```

Bind-mount `php.ini` into the `www` service in your `docker-compose.yml` file:

```
    volumes:
      ...
      - './php.ini:/usr/local/etc/php/conf.d/farmos.ini'
```

## Updating

**Important:** Read and understand the [Updating farmOS](/hosting/update)
documentation first. Updating the Docker image is only one part of the overall
update process.

If you are using the official farmOS Docker image, you can update to a new
release by changing the `x.y.z` version number in the `docker run` command or
`docker-compose.yml` configuration file described above and restarting the
container(s).

If you are using [Docker Compose](#docker-compose), you must run
`docker compose down` to destroy the old container before running
`docker compose up` to create the new one.

Assuming that `/opt/drupal/web/sites` is persisted, this will update the farmOS
codebase (which is located in `/opt/drupal` within the container), while
preserving `settings.php` and uploaded files. See [Persistence](#persistence)
above for more information.

After the container is updated, perform the manual database update steps
described in the [Updating farmOS](/hosting/update) documentation.
