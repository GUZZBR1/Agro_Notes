<?php

/**
 * @file
 * Post update functions for farm_ui_location module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_ui_location_removed_post_updates() {
  return [
    'farm_ui_location_post_update_add_locations_map_type' => '4.x',
  ];
}
