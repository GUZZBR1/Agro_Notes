<?php

/**
 * @file
 * Post update hooks for the farm_map module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_map_removed_post_updates() {
  return [
    'farm_map_post_update_generalize_geofield_map_types_behavior' => '4.x',
  ];
}
