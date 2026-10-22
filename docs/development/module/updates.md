# Automated updates

## Update hooks

farmOS modules may change and evolve over time. If these changes require
updates to a farmOS database or configuration, then update logic should be
provided so that users of the module can perform the necessary changes
automatically when they update to the new version.

This logic can be supplied via implementations of `hook_update_N()` and
`hook_post_update_NAME()`.

For more information, see the documentation for Drupal's
[Update API](https://www.drupal.org/docs/drupal-apis/update-api/).

## Configuration updates

The farmOS Update module (`farm_update`) provides a feature for automatically
reverting configuration entities to match their module-provided YML definitions.
This allows module developers to make changes to the YML files in a module's
`config/install` directory without providing a corresponding update hook to
deploy that change to existing databases (because `config/install` YML is
normally only used when a module is first installed). With this module enabled,
overridden configuration will be reverted whenever caches are rebuilt.

This is an opt-in feature, and each "managed" configuration item must be
explicitly declared in either `hook_farm_update_managed_config()` or in the
`farm_update.settings.managed_config` settings. See examples below for more
information.

Note that this only handles overridden configuration. It does not handle
missing, inactive, or added configuration. It also does not touch "simple"
configuration (eg: module settings) - only configuration entities (eg: Views).

If your module is adding or deleting configuration, the recommended approach is
to implement `hook_post_update_NAME()` to perform the necessary operations.

### Example `hook_farm_update_managed_config()`

A module can declare configuration items that should be automatically reverted
with an implementation of `hook_farm_update_managed_config()` that returns an
array of configuration names. For example, in `src/Hook/UpdateHooks.module`:

```php
<?php

declare(strict_types=1);

namespace Drupal\mymodule\Hook;

use Drupal\Core\Hook\Attribute\Hook;

/**
 * Update hook implementations for mymodule.
 */
class UpdateHooks {

  /**
   * Implements hook_farm_update_managed_config().
   */
  #[Hook('farm_update_managed_config')]
  public function farmUpdateManagedConfig() {
  
    // Automatically update the mymodule_custom View configuration.
    return [
      'views.view.mymodule_custom',
    ];
  }

}
```

### Example `farm_update.settings`

The farmOS Update module will also check the `managed_config` setting in
its own `farm_update.settings` configuration for a list of configuration
items to automatically update. This can be provided by a custom module in
`config/install/farm_update.settings.yml`, or synced/imported into active
configuration by other means.

For example, in `farm_update.settings.yml`:

```yaml
managed_config:
  # Automatically update the mymodule_custom View configuration.
  - views.view.mymodule_custom
```

### Disable farmOS Update module

In some cases, such as deployments that manager their configuration sync
directory changes in source control, automatic changes to configuration may not
be desirable.

The easiest way to disable automatic configuration updates is to turn off the
`farm_update` module. This can be done via Drush:

    drush pm-uninstall farm_update

This will completely disable automatic reverts of configuration. You can then
manage all configuration changes and deployment manually. One way to do this
is with the `config_update_ui` module, which provides a report of all missing,
inactive, added, and changed configuration. This can be enabled via Drush:

    drush en config_update_ui

Then go to `/admin/config/development/configuration/report/type/system.all` to
see the full report. Individual configuration items can be reverted, imported,
and deleted.
