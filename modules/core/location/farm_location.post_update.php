<?php

/**
 * @file
 * Post update hooks for the farm_location module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_location_removed_post_updates() {
  return [
    'farm_location_post_update_uninstall_asset_move_action' => '4.x',
  ];
}
