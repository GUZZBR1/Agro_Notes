<?php

/**
 * @file
 * Post update functions for farm_import module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_import_removed_post_updates() {
  return [
    'farm_import_post_update_install_farm_setup' => '4.x',
  ];
}
