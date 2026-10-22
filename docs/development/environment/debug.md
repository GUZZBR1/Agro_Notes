# Debugging

The farmOS development Docker image comes pre-installed with
[XDebug](https://xdebug.org) 3, which allows debugger connections on port 9003.

XDebug can be configured to discover the client host automatically with the
following `extra_hosts` and `environment` configuration in `docker-compose.yml`:

    extra_hosts:
    - host.docker.internal:host-gateway
    environment:
      XDEBUG_MODE: debug
      XDEBUG_CONFIG: client_host=host.docker.internal
      XDEBUG_SESSION: 1
      PHP_IDE_CONFIG: serverName=localhost

## IDEs

### VSCode / VSCodium

In VSCode / VSCodium, install the
[XDebug extension](https://marketplace.visualstudio.com/items?itemName=xdebug.php-debug)
(`xdebug.php-debug`), then create a `launch.json` file in your `.vscode`
project directory with the following content:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Listen for Xdebug",
            "type": "php",
            "request": "launch",
            "hostname": "0.0.0.0",
            "port": 9003,
            "pathMappings": {
                "/opt/drupal": "${workspaceRoot}"
            }
        }
    ]
}
```

Then go to Run > Start Debugging to start listening for XDebug connections, add
a breakpoint in your code, load a page in your browser, and you should see a
prompt appear in VSCode / VSCodium that will begin the debugging session and
pause execution at your breakpoint.

### PHPStorm

In PHPStorm, enable the "Start listening for PHP Debug Connections" option, add
a breakpoint in your code, load the page in your browser, and you should see a
prompt appear in PHPStorm that will begin the debugging session and pause
execution at your breakpoint.

Path mappings will be automatically configured to map your local `www/web`
directory to `/opt/drupal/web` inside the container, but this will only work
for requests made through the browser. It is recommended that `www` is mapped
to `/opt/drupal` instead. This will allow debugging with `drush` or `composer`
commands, as well as code in
[local repositories](/development/environment/repositories).

Path mappings can be configured in PHPStorm Settings > PHP > Servers.

## Drush commands

Drush disables XDebug by default. Run with the `--xdebug` flag to enable it.

For example: `drush --xdebug status`
