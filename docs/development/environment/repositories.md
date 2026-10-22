# Managing local Git repositories

If you are developing a farmOS module that you plan to share with others, or if
you want to work on core farmOS development, you will need to set up local Git
repositories for each project that you want to contribute to. This guide
describes how to do this.

First, it helps to understand how Composer is used to build a farmOS codebase
for deployment. See [Building farmOS with Composer](/hosting/composer) for more
information.

Normally, Composer will pull packages from official sources like
[packagist.org](https://packagist.org/) or
[packages.drupal.org](https://packages.drupal.org/). It is also possible to tell
Composer to pull packages from Git repositories that are checked out locally,
and maintain a symlink to it from its proper place in the codebase.

This allows you to run [Composer commands](/development/composer) like
`composer update` without risk of losing or overwriting changes to your local
Git repositories.

## Setup

To set up a local package, two changes are necessary in the top-level
`composer.json` for your codebase:

1. Add an entry to the `repositories` section that points to the local Git
   repository with a type of `path`. This tells Composer where to find the
   package locally. The `url` should be relative to the location of the
   `composer.json` file.
2. Set the version constraint for your package to `*` in the `require` section.
   This tells Composer to use whatever version is currently checked out  in the
   local Git repository.

Once that is done, run `composer update` to tell Composer to find your local
package and create the appropriate symlink to it within the codebase.

### Example

For example, if you want to work on farmOS core, the first step is to clone
the farmOS Git repository into a local directory. Create a directory called
`repos` alongside your `composer.json` file, and clone the repository into it.

Assuming you are starting with a default
[local development environment](/development/environment) your `composer.json`
will be located inside the `www` bind-mount volume directory.

```bash
mkdir repos
cd repos
git clone --branch 4.x https://github.com/farmOS/farmOS.git
```

The `composer.json` file (in a default
[local development environment](/development/environment)) will include the
following `repositories` and `require` sections:

```json
    ...
    "repositories": [
        {
            "name": "farmos",
            "type": "git",
            "url": "https://github.com/farmOS/farmOS"
        },
        {
            "type": "composer",
            "url": "https://packages.drupal.org/8"
        }
    ],
    "require": {
        "farmos/farmos": "^4.0",
        ...
```

After making the modifications described above, it should look like this:

```json
    ...
    "repositories": [
        {
            "name": "farmos",
            "type": "path",
            "url": "repos/farmOS",
        },
        {
            "type": "composer",
            "url": "https://packages.drupal.org/8"
        }
    ],
    "require": {
        "farmos/farmos": "*",
        ...
```

After running `composer update`, your local instance of farmOS will now be using
the code from your local Git repository.

If you want to add another repository (eg: for an add-on module), simply add
an additional `repositories` section, and `require` line. For example:

```json
    ...
    "repositories": [
        {
            "name": "farmos",
            "type": "path",
            "url": "repos/farmOS",
        },
        {
            "name": "mymodule",
            "type": "path",
            "url": "repos/mymodule",
        },
        {
            "type": "composer",
            "url": "https://packages.drupal.org/8"
        }
    ],
    "require": {
        "farmos/farmos": "*",
        "myorg/mymodule": "*",
        ...
```

Replace `mymodule` with your module name and `myorg/mymodule` with the package
name from your module's `composer.json` file.

Run `composer update` to use your local repository.

### Tips

- If you are running farmOS in Docker (as described in the official
  [local environment setup guide](/development/environment)), you will need to
  make sure that the local repository is mounted into the Docker container, and
  that the `"url"` is relative to the location of `composer.json` file inside
  the container. The example above makes a `repos` directory inside the existing
  mounted volume.
- If you are working on a module that is hosted on
  [packages.drupal.org](https://packages.drupal.org/), be sure to put your local
  package's `path` entry above the `packages.drupal.org` entry in the
  `repositores` section of `composer.json`, otherwise the official package may
  still take precedence over your local one.
