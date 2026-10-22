<?php

/**
 * @file
 * Post update hooks for the farm_migrate module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_migrate_removed_post_updates() {
  return [
    'farm_migrate_post_update_uninstall_v1_migrations' => '4.x',
  ];
}
