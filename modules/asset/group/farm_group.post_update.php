<?php

/**
 * @file
 * Post update hooks for the farm_group module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_group_removed_post_updates() {
  return [
    'farm_group_post_update_uninstall_asset_group_action' => '4.x',
  ];
}
