<?php

/**
 * @file
 * Updates farm_entity_fields module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_entity_fields_removed_post_updates() {
  return [
    'farm_entity_fields_post_update_enable_farm_parent' => '4.x',
    'farm_entity_fields_post_update_add_term_external_uri' => '4.x',
    'farm_entity_fields_post_update_install_farm_image' => '4.x',
  ];
}
