<?php

declare(strict_types=1);

namespace Drupal\farm_role\Access;

use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Session\AccessPolicyBase;
use Drupal\Core\Session\AccountInterface;
use Drupal\Core\Session\CalculatedPermissionsItem;
use Drupal\Core\Session\RefinableCalculatedPermissionsInterface;
use Drupal\farm_role\ManagedRolePermissionsManagerInterface;

/**
 * Grants permissions based on the user's role and managed role permissions.
 */
final class ManagedRolePermissionsAccessPolicy extends AccessPolicyBase {

  public function __construct(
    protected EntityTypeManagerInterface $entityTypeManager,
    protected ManagedRolePermissionsManagerInterface $managed_role_permissions_manager,
  ) {}

  /**
   * {@inheritdoc}
   */
  public function calculatePermissions(AccountInterface $account, string $scope): RefinableCalculatedPermissionsInterface {
    $calculated_permissions = parent::calculatePermissions($account, $scope);

    /** @var \Drupal\user\RoleInterface[] $user_roles */
    $user_roles = $this->entityTypeManager->getStorage('user_role')->loadMultiple($account->getRoles());
    foreach ($user_roles as $role) {
      $calculated_permissions
        ->addItem(new CalculatedPermissionsItem(
          $this->managed_role_permissions_manager->getManagedRolePermissions($role),
          $role->isAdmin(),
        ))
        ->addCacheableDependency($role);
    }

    return $calculated_permissions;
  }

  /**
   * {@inheritdoc}
   */
  public function getPersistentCacheContexts(): array {
    return ['user.roles'];
  }

}
