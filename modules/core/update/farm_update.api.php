<?php

/**
 * @file
 * Hooks provided by farm_update.
 *
 * This file contains no working PHP code; it exists to provide additional
 * documentation for doxygen as well as to document hooks in the standard
 * Drupal manner.
 */

declare(strict_types=1);

/**
 * @addtogroup hooks
 * @{
 */

/**
 * Specify config items that should be automatically updated.
 *
 * @return array
 *   An array of config item names.
 */
function hook_farm_update_managed_config() {
  return [
    'views.view.farm_log',
    'asset.type.structure',
  ];
}

/**
 * @} End of "addtogroup hooks".
 */
