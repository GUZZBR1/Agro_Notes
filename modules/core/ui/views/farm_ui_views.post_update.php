<?php

/**
 * @file
 * Post update functions for farm_ui_views module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_ui_views_removed_post_updates() {
  return [
    'farm_ui_views_post_update_enable_collapsible_filter' => '4.x',
    'farm_ui_views_post_update_install_farm_export_csv' => '4.x',
    'farm_ui_views_post_update_farm_log_quantity' => '4.x',
  ];
}
