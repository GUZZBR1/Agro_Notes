<?php

/**
 * @file
 * Post update functions for farm_ui_map module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_ui_map_removed_post_updates() {
  return [
    'farm_ui_map_post_update_locations_behavior' => '4.x',
  ];
}
