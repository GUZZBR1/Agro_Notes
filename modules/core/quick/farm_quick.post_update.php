<?php

/**
 * @file
 * Post update hooks for the farmOS Quick Form module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_quick_removed_post_updates() {
  return [
    'farm_quick_post_update_install_quick_form_entity_type' => '4.x',
  ];
}
