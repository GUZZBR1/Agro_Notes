<?php

/**
 * @file
 * Post update functions for farm_kml module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_kml_removed_post_updates() {
  return [
    'farm_kml_post_update_move_kml_export_actions' => '4.x',
  ];
}
