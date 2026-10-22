<?php

/**
 * @file
 * Post update functions for farm_role_account_admin module.
 */

declare(strict_types=1);

use Drupal\user\Entity\Role;
use Drupal\user\Entity\User;

/**
 * Move farm_account_admin role module and grant farm_config_admin role.
 */
function farm_role_account_admin_post_update_move_module(&$sandbox = NULL) {

  // Make a list of users with the farm_account_admin role.
  $query = \Drupal::entityQuery('user');
  $query->accessCheck(FALSE);
  $query->condition('roles', 'farm_account_admin');
  $uids = $query->execute();

  // Remember the allow_peer_role_assignment setting.
  $allow_peer_role_assignment = \Drupal::config('farm_role_account_admin.settings')->get('allow_peer_role_assignment');

  // Uninstall this module, if no other installed modules depend on it.
  if (\Drupal::service('module_handler')->moduleExists('farm_role_account_admin')) {
    $modules = \Drupal::service('extension.list.module')->reset()->getList();
    $installed_dependents = [];
    if (!empty($modules['farm_role_account_admin']->required_by)) {
      foreach (array_keys($modules['farm_role_account_admin']->required_by) as $module) {
        if (\Drupal::service('module_handler')->moduleExists($module)) {
          $installed_dependents[] = $module;
        }
      }
    }
    if (empty($installed_dependents)) {
      \Drupal::service('module_installer')->uninstall(['farm_role_account_admin']);
    }
  }

  // Delete the farm_account_admin role, in case the module was not uninstalled.
  $role = Role::load('farm_account_admin');
  if (!is_null($role)) {
    $role->delete();
  }

  // If there are no users with the farm_account_admin role, stop here.
  if (empty($uids)) {
    return;
  }

  // Install the farm_account_admin and farm_config_admin modules.
  \Drupal::service('module_installer')->install([
    'farm_account_admin',
    'farm_config_admin',
  ]);

  // Grant the farm_account_admin and farm_config_admin roles to all users who
  // had the farm_account_admin role originally.
  foreach ($uids as $uid) {
    $user = User::load($uid);
    $user->addRole('farm_account_admin');
    $user->addRole('farm_config_admin');
    $user->save();
  }

  // Restore the allow_peer_role_assignment setting.
  if ($allow_peer_role_assignment) {
    $config = \Drupal::configFactory()->getEditable('farm_account_admin.settings');
    $config->set('allow_peer_role_assignment', $allow_peer_role_assignment);
    $config->save();
  }
}
