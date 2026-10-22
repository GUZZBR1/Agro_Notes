<?php

/**
 * @file
 * Post update hooks for the farm_lab_test module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_lab_test_removed_post_updates() {
  return [
    'farm_lab_test_post_update_add_received_processed_date_fields' => '4.x',
    'farm_lab_test_post_update_enable_farm_lab' => '4.x',
    'farm_lab_test_post_update_migrate_lab_terms' => '4.x',
    'farm_lab_test_post_update_enable_farm_quantity_test' => '4.x',
    'farm_lab_test_post_update_add_tissue_type' => '4.x',
    'farm_lab_test_post_update_override_lab_test_timestamp_label_description' => '4.x',
    'farm_lab_test_post_update_soil_texture' => '4.x',
  ];
}
