<?php

/**
 * @file
 * Post update hooks for the farm_quick_movement module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_quick_movement_removed_post_updates() {
  return [
    'farm_quick_movement_post_update_install_quick_movement_action' => '4.x',
  ];
}
