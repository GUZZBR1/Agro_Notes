<?php

/**
 * @file
 * Post update functions for farm_setup module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_setup_removed_post_updates() {
  return [
    'farm_setup_post_update_uninstall_farm_settings' => '4.x',
  ];
}
