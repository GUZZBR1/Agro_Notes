<?php

/**
 * @file
 * Post update hooks for the farm_export_csv module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_export_csv_removed_post_updates() {
  return [
    'farm_export_csv_post_update_quantity_csv_action' => '4.x',
  ];
}
