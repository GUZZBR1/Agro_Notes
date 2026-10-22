<?php

/**
 * @file
 * Post update hooks for the farm_import_csv module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_import_csv_removed_post_updates() {
  return [
    'farm_import_csv_post_update_install_farm_migrate' => '4.x',
    'farm_import_csv_post_update_uninstall_migrate_source_ui' => '4.x',
  ];
}
