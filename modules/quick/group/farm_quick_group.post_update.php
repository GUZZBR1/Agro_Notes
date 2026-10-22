<?php

/**
 * @file
 * Post update hooks for the farm_quick_group module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_quick_group_removed_post_updates() {
  return [
    'farm_quick_group_post_update_install_quick_group_action' => '4.x',
  ];
}
