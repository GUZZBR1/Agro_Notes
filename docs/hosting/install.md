# Installing farmOS

These instructions are for installing farmOS on a live production server.
For local development/testing, please refer to the
[development environment](/development/environment)
documentation.

Refer to the [farmOS server requirements](/hosting/requirements) documentation
to understand what is needed for hosting farmOS.

## farmOS Server

Docker is the recommended method of hosting farmOS because it encapsulates the
server level dependencies that farmOS needs. To deploy a farmOS codebase with
Docker, see [farmOS in Docker](/hosting/docker).

If you need to build a more customized farmOS codebase, including modules
provided by the community, or custom modules written by yourself, see
[Building farmOS with Composer](/hosting/composer).

If you do not have access to Docker or Composer,
[pre-built "packaged" releases](/hosting/prebuilt) are also available.

## Installing farmOS

Once you have the farmOS codebase deployed, and a database server provisioned,
you can proceed with the web-based farmOS installation. Visit the farmOS
server's hostname in your browser and follow the steps to install farmOS and
optional modules.

### File uploads

In order to upload files, a private filesystem path must be configured in the
`settings.php` file after installation is complete.

If you are using the official Docker image, and bind-mounting the `sites`
directory as a volume, add the following line to `sites/default/settings.php`:

    $settings['file_private_path'] = '/opt/drupal/web/sites/default/private/files';

Additionally, create the folder `/opt/drupal/web/sites/default/private/`.

Set the correct user and permissions:

Folder ownership and group should match the web server user. If you are using
the farmOS Docker image (running Apache), this will be `www-data`.

Folder permissions should be set to `770` or `drwxrwx---`.

Finally, make sure to clear the caches by visiting Administration >
Configuration > Development > Performance and clicking the `Clear all caches`
button, or use Drush via the command line: `drush cr`.

### Cron

farmOS performs routine tasks via its built-in cron. This includes database
cleanup and garbage collection. A cron job must be configured on the host
system to trigger this. There are three ways to do this:

**1. Via the `drush cron` command (recommended)**

The Drush command-line tool provides a `cron` command for triggering the
execution of cron tasks. This can be run via a scheduled system `crontab`.
Weekly is enough for most use-cases.

The actual `drush` command will vary depending on how/where you have farmOS
installed. Drush is located in `vendor/bin/drush` within the farmOS codebase,
and may require additional arguments to find your farmOS database correctly.
For more information, see the [Drush cron documentation](https://www.drush.org/latest/cron).

If you are running farmOS in the official Docker container, your `crontab`
will look something like this (replace `[container-name]` with the name of your
running farmOS container):

`4 0 * * 0 sudo docker exec -it [container-name] drush cron > /dev/null`

**2. Via the secret cron URL**

A special URL is available for running cron via an HTTP request. This URL
includes a secret key to prevent it from being run by unauthorized requests.
To find the secret cron URL, while logged in as a farmOS administrator, go to
Administration > Configuration > System > Cron. The URL will look like this:

`https://[base-url]/cron/[secret-key]`

Use `wget` in a Linux cron job to request this URL on a schedule. Weekly is
enough for most use-cases.

`4 0 * * 0 wget -O - -q -t 1 [cron-url] > /dev/null`

The only disadvantage of this approach is it may run into PHP `memory_limit` or
`max_execution_time` restrictions, if the cron tasks are particularly long or
complex.

**3. Via the "Automated Cron" module (not recommended)**

Drupal also includes an "Automated Cron" module, which is disabled by default
in farmOS. When enabled, this module will automatically perform cron tasks at
the end of normal visitor requests. This option is only recommended if your
host system does not have the ability to configure cron jobs. It can cause
random requests to farmOS to be very slow, as the cron tasks are tacked onto
the normal page loading process.

### OAuth2 keys

If you need to connect to the farmOS API from an outside source, you will need
to install the farmOS API OAuth2 Server module (`farm_api_oauth`) and generate
public/private keypair files for OAuth2 tokens in a `keys` directory outside the
webroot.

As the system administrator (user 1), go to Administration > Configuration > Web
Services > Consumers in the main menu, then click the Settings tab. The "Public
Key" and "Private Key" paths can be set relative to the webroot (eg:
`../keys/public.key` and `../keys/private.key`). The "Generate keys" button at
the bottom of this form will attempt to create the key files. The `keys`
directory must be writable by the HTTP server user (which is `www-user` in the
official farmOS Docker container), but should be protected from writing after
the keys are generated.

If you are running farmOS in Docker with the recommended
[Docker Compose](/hosting/docker/#docker-compose) configuration, a `keys`
directory is bind-mounted to persist the generated keys.
