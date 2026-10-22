<?php

/**
 * @file
 * Post update hooks for the farm_structure module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_structure_removed_post_updates() {
  return [
    'farm_structure_post_update_add_other_structure_type' => '4.x',
  ];
}
