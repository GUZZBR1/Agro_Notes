<?php

declare(strict_types=1);

namespace Drupal\farm_update_test\Hook;

use Drupal\Core\Hook\Attribute\Hook;

/**
 * Update hook implementations for farm_update_test.
 */
class UpdateHooks {

  /**
   * Implements hook_farm_update_managed_config().
   */
  #[Hook('farm_update_managed_config')]
  public function farmUpdateManagedConfig() {
    return [

      // Declare this config as "managed" so it will be automatically reverted
      // if it is overridden.
      'farm_flag.flag.priority',

      // Also declare this config as "managed", but we will remove it in
      // hook_farm_update_managed_config_alter() below.
      'farm_flag.flag.test',
    ];
  }

  /**
   * Implements hook_farm_update_managed_config_alter().
   */
  #[Hook('farm_update_managed_config_alter')]
  public function farmUpdateManagedConfigAlter(array &$config) {

    // Remove an item from the list of managed config.
    if (in_array('farm_flag.flag.test', $config)) {
      unset($config[array_search('farm_flag.flag.test', $config)]);
    }
  }

}
