<?php

declare(strict_types=1);

namespace Drupal\farm_role\Plugin\ScopeGranularity;

use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Plugin\ContainerFactoryPluginInterface;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\farm_role\ManagedRolePermissionsManagerInterface;
use Drupal\simple_oauth\Attribute\ScopeGranularity;
use Drupal\simple_oauth\Plugin\ScopeGranularity\Role;
use Symfony\Component\DependencyInjection\ContainerInterface;

/**
 * The Managed Role scope granularity plugin.
 */
#[ScopeGranularity(
  'managed_role',
  new TranslatableMarkup('Managed Role'),
)]
class ManagedRole extends Role implements ContainerFactoryPluginInterface {

  public function __construct(
    array $configuration,
    string $pluginId,
    array $pluginDefinition,
    protected EntityTypeManagerInterface $entityTypeManager,
    protected ManagedRolePermissionsManagerInterface $managedRolePermissionsManager,
  ) {
    parent::__construct($configuration, $pluginId, $pluginDefinition, $entityTypeManager);
  }

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container, array $configuration, $pluginId, $pluginDefinition) {
    // @todo Use autowiring and remove this when the parent class does.
    return new static(
      $configuration,
      $pluginId,
      $pluginDefinition,
      $container->get('entity_type.manager'),
      $container->get('plugin.manager.managed_role_permissions'),
    );
  }

  /**
   * {@inheritdoc}
   */
  public function defaultConfiguration() {
    return [
      'role' => NULL,
    ];
  }

  /**
   * {@inheritdoc}
   */
  public function hasPermission(string $permission): bool {
    $has_permission = parent::hasPermission($permission);
    $role_id = $this->getConfiguration()['role'];
    if (!$has_permission && $role = $this->entityTypeManager->getStorage('user_role')->load($role_id)) {
      $has_permission = $this->managedRolePermissionsManager->isPermissionInRole($permission, $role);
    }
    return $has_permission;
  }

  /**
   * {@inheritdoc}
   */
  public function getPermissions(): array {
    $permissions = parent::getPermissions();
    $role_id = $this->getConfiguration()['role'];
    $role = $this->entityTypeManager->getStorage('user_role')->load($role_id);
    return array_unique(array_merge($permissions, $this->managedRolePermissionsManager->getManagedRolePermissions($role)));
  }

  /**
   * Gets the role options.
   *
   * @return \Drupal\Core\StringTranslation\TranslatableMarkup[]
   *   Returns the role options.
   */
  protected function getRoleOptions(): array {
    $options = [];
    foreach ($this->managedRolePermissionsManager->getMangedRoles() as $role) {
      $options[$role->id()] = $role->label();
    }
    return $options;
  }

}
