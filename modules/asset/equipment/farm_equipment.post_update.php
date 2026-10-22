<?php

/**
 * @file
 * Post update hooks for the farm_equipment module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_equipment_removed_post_updates() {
  return [
    'farm_equipment_post_update_install_equipment_type' => '4.x',
  ];
}
