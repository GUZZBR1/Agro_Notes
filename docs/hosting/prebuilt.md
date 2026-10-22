# Pre-built farmOS releases

**Important**: It is highly recommended that you use [Docker](/hosting/docker)
and/or [Composer](/hosting/composer) for hosting farmOS. Together they
encapsulate all the [web server requirements](/hosting/requirements/#web-server)
and ensure that all dependencies are compatible with one another. **This is
especially important if you want to install additional add-on modules provided
by the community.**

If you do not have access to these tools in your hosting environment (eg: in
[shared hosting](https://en.wikipedia.org/wiki/Shared_web_hosting_service)
contexts), your options for hosting farmOS will be more limited, and installing
add-on modules may not be possible (or will require more understanding of the
requirements and considerations for maintaining them and their dependencies).

In an effort to make farmOS available in these contexts, pre-built "packaged"
releases are provided for download. These are simply
[tarballs](https://en.wikipedia.org/wiki/Tar_(computing)) that contain a farmOS
codebase that can be unpacked in a web server's webroot directory. They are
automatically built by the official farmOS build process, using Docker and
Composer, and are identical to the code included in the official farmOS Docker
images.

**Please be aware of the following limitations:**

- Pre-built "packaged" released only include a default "stock" farmOS codebase.
- You are responsible for all [server requirements](/hosting/requirements).
- Installing community add-on modules is more difficult (see
  [Build your own](#build-your-own) for a suggested approach).
- No support is provided by the farmOS maintainers.

## Overview

An alternative to the Docker-based deployment is to install the farmOS codebase
directly on the host server using a packaged release tarball, available from
GitHub: [github.com/farmOS/farmOS/releases](https://github.com/farmOS/farmOS/releases)

Packaged releases include everything from the `/opt/drupal` directory in the
Docker image. This represents the entire farmOS codebase, pre-built with
[Composer](https://getcomposer.org).

Download and unpack the tarball on your web server, and point the document root
at the `web` subdirectory.

Once the farmOS codebase is in place on your web server, continue with the
[farmOS installation steps](/hosting/install).

## Updating

**Important:** Read and understand the [Updating farmOS](/hosting/update)
documentation first. Updating the farmOS code is only one part of the overall
update process.

When a new version of farmOS is released, you can update to it by downloading
the new release tarball and unpacking it in place of the old codebase, replacing
everything except the `web/sites` directory. Be sure to *replace* (not *merge*)
all files and directories.

**Do not overwrite the `web/sites` directory, because it contains all your
site-specific settings and uploaded files.**

## Build your own

If you want to install community add-on modules, but can't run Docker or
Composer in your hosting environment, one approach is to build your own farmOS
codebase locally with Composer and create your own tarball. This mimics the way
the official pre-built "packaged" releases are created, but gives you more
control over defining your own dependencies. For more information, see
[Building farmOS with Composer](/hosting/composer).
