<?php

/**
 * @file
 * Post update hooks for the farm_plant_type module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_plant_type_removed_post_updates() {
  return [
    'farm_plant_type_post_update_delete_display_config' => '4.x',
    'farm_plant_type_post_update_min_1_day' => '4.x',
    'farm_plant_type_post_update_add_harvest_days' => '4.x',
    'farm_plant_type_post_update_move_transplant_days' => '4.x',
  ];
}
