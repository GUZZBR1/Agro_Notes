<?php

/**
 * @file
 * Post update functions for farm_manager module.
 */

declare(strict_types=1);

/**
 * Add manager permissions to manager role.
 */
function farm_manager_update_add_manager_permissions(&$sandbox) {
  $role = \Drupal::configFactory()->getEditable('user.role.farm_manager');
  $settings = $role->get('third_party_settings');
  if (empty($settings['farm_role']['access']['manager'])) {
    $settings['farm_role']['access']['manager'] = TRUE;
    $role->set('third_party_settings', $settings);
    $role->save();
  }
}

/**
 * Remove config permissions from manager role.
 */
function farm_manager_update_remove_config_permissions(&$sandbox) {
  $role = \Drupal::configFactory()->getEditable('user.role.farm_manager');
  $settings = $role->get('third_party_settings');
  if (!empty($settings['farm_role']['access']['config'])) {
    $settings['farm_role']['access']['config'] = FALSE;
    $role->set('third_party_settings', $settings);
    $role->save();
  }
}
