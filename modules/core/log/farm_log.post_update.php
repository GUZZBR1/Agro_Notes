<?php

/**
 * @file
 * Post update hooks for the farm_log module.
 */

declare(strict_types=1);

use Drupal\system\Entity\Action;

/**
 * Move asset_add_log_action to farm_log_asset module.
 */
function farm_log_post_update_move_asset_add_log_action(&$sandbox) {

  // Update the action's dependency from farm_log to farm_log_asset.
  $action = Action::load('asset_add_log_action');
  if (!is_null($action)) {
    $dependencies = $action->getDependencies();
    if (($key = array_search('farm_log', $dependencies['module'])) !== FALSE) {
      unset($dependencies['module'][$key]);
      $dependencies['module'][] = 'farm_log_asset';
      $action->set('dependencies', $dependencies);
      $action->save();
    }
  }
}

/**
 * Implements hook_removed_post_updates().
 */
function farm_log_removed_post_updates() {
  return [
    'farm_log_post_update_farm_log_workflow' => '4.x',
  ];
}
