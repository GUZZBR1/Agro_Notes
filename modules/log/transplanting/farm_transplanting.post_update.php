<?php

/**
 * @file
 * Post update hooks for the farm_transplanting module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_transplanting_removed_post_updates() {
  return [
    'farm_transplanting_post_update_restore_transplant_days' => '4.x',
  ];
}
