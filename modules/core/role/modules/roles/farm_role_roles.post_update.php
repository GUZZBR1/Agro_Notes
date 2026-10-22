<?php

/**
 * @file
 * Post update functions for farm_role_roles module.
 */

declare(strict_types=1);

use Drupal\user\Entity\Role;
use Drupal\user\Entity\User;

/**
 * Split farm_role_roles module into farm_manager, farm_worker, farm_viewer.
 */
function farm_role_roles_post_update_split_module(&$sandbox = NULL) {

  // Define the roles we will be migrating.
  $roles = [
    'farm_manager',
    'farm_viewer',
    'farm_worker',
  ];

  // Make a list of users with each role.
  $uids = [];
  foreach ($roles as $role) {
    $query = \Drupal::entityQuery('user');
    $query->accessCheck(FALSE);
    $query->condition('roles', $role);
    $uids[$role] = $query->execute();
  }

  // Uninstall this module, if no other installed modules depend on it.
  if (\Drupal::service('module_handler')->moduleExists('farm_role_roles')) {
    $modules = \Drupal::service('extension.list.module')->reset()->getList();
    $installed_dependents = [];
    if (!empty($modules['farm_role_roles']->required_by)) {
      foreach (array_keys($modules['farm_role_roles']->required_by) as $module) {
        if (\Drupal::service('module_handler')->moduleExists($module)) {
          $installed_dependents[] = $module;
        }
      }
    }
    if (empty($installed_dependents)) {
      \Drupal::service('module_installer')->uninstall(['farm_role_roles']);
    }
  }

  // Delete the old roles, in case the module was not uninstalled.
  foreach ($roles as $role_name) {
    $role = Role::load($role_name);
    if (!is_null($role)) {
      $role->delete();
    }
  }

  // Grant the new roles to the users who had them originally.
  // Only install the new modules if necessary.
  foreach ($roles as $role) {
    if (empty($uids[$role])) {
      continue;
    }
    \Drupal::service('module_installer')->install([$role]);
    foreach ($uids[$role] as $uid) {
      $user = User::load($uid);
      $user->addRole($role);
      $user->save();
    }
  }
}
