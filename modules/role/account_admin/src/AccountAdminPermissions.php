<?php

declare(strict_types=1);

namespace Drupal\farm_account_admin;

use Drupal\Core\Config\ConfigFactoryInterface;
use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\DependencyInjection\ContainerInjectionInterface;
use Drupal\farm_role\ManagedRolePermissionsManagerInterface;
use Drupal\user\RoleInterface;

/**
 * Add permissions to the Account Admin role.
 */
class AccountAdminPermissions implements ContainerInjectionInterface {

  use AutowireTrait;

  public function __construct(
    protected ManagedRolePermissionsManagerInterface $managedRolePermissionsManager,
    protected ConfigFactoryInterface $configFactory,
  ) {}

  /**
   * Add permissions to default farmOS roles.
   *
   * @param \Drupal\user\RoleInterface $role
   *   The role to add permissions to.
   *
   * @return array
   *   An array of permission strings.
   */
  public function permissions(RoleInterface $role) {
    $perms = [];

    // Add permissions to the farm_account_admin role.
    if ($role->id() == 'farm_account_admin') {

      // Load the module settings.
      $settings = $this->configFactory->get('farm_account_admin.settings');

      // Grant the ability to assign managed farmOS roles.
      $roles = $this->managedRolePermissionsManager->getMangedRoles();
      foreach ($roles as $role) {

        // Do not allow assigning the "Account Admin" role if
        // allow_peer_role_assignment is disabled.
        if ($role->id() == 'farm_account_admin' && !$settings->get('allow_peer_role_assignment')) {
          continue;
        }

        // Add permission to assign the role.
        $perms[] = 'assign ' . $role->id() . ' role';
      }
    }

    return $perms;
  }

}
