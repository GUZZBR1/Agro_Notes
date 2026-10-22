<?php

declare(strict_types=1);

namespace Drupal\farm_role;

use Drupal\Core\Cache\CacheBackendInterface;
use Drupal\Core\Controller\ControllerResolverInterface;
use Drupal\Core\Entity\EntityTypeBundleInfoInterface;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Extension\ModuleHandlerInterface;
use Drupal\Core\Plugin\DefaultPluginManager;
use Drupal\Core\Plugin\Discovery\ContainerDerivativeDiscoveryDecorator;
use Drupal\Core\Plugin\Discovery\YamlDiscovery;
use Drupal\user\RoleInterface;
use Symfony\Component\DependencyInjection\Attribute\Autowire;

/**
 * ManagedRolePermissions Plugin Manager.
 *
 * @internal
 *
 * @ingroup farm
 */
class ManagedRolePermissionsManager extends DefaultPluginManager implements ManagedRolePermissionsManagerInterface {

  /**
   * Default values for each FarmRolePermissions plugin.
   *
   * @var array
   */
  protected $defaults = [
    'class' => 'Drupal\farm_role\ManagedRolePermissions',
    'default_permissions' => [],
    'manager_permissions' => [],
    'config_permissions' => [],
    'permission_callbacks' => [],
  ];

  /**
   * An array of role permissions keyed by role ID.
   *
   * @var array
   */
  protected $rolePermissions = [];

  public function __construct(
    #[Autowire(service: 'container.namespaces')]
    \Traversable $namespaces,
    #[Autowire(service: 'cache.discovery')]
    CacheBackendInterface $cache_backend,
    ModuleHandlerInterface $module_handler,
    protected ControllerResolverInterface $controllerResolver,
    protected EntityTypeBundleInfoInterface $entityTypeBundleInfo,
    protected EntityTypeManagerInterface $entityTypeManager,
  ) {
    parent::__construct(
      'Plugin/ManagedRolePermissions',
      $namespaces,
      $module_handler
    );
    $this->alterInfo('managed_role_permissions_info');
    $this->setCacheBackend($cache_backend, 'managed_role_permissions_plugins');
  }

  /**
   * {@inheritdoc}
   */
  protected function getDiscovery() {
    // PHPStan level 3+ throws the following error on the next line:
    // Negated boolean expression is always false.
    // We ignore this because we are following Drupal core's pattern.
    // @phpstan-ignore booleanNot.alwaysFalse
    if (!$this->discovery) {
      $discovery = new YamlDiscovery('managed_role_permissions', $this->moduleHandler->getModuleDirectories());
      $this->discovery = new ContainerDerivativeDiscoveryDecorator($discovery);
    }
    return $this->discovery;
  }

  /**
   * {@inheritdoc}
   */
  public function getMangedRoles(): array {
    /** @var \Drupal\user\RoleInterface[] $roles */
    $roles = $this->entityTypeManager->getStorage('user_role')->loadMultiple();
    return array_filter($roles, function ($role) {
      return $this->isManagedRole($role);
    });
  }

  /**
   * {@inheritdoc}
   */
  public function isManagedRole(RoleInterface $role) {
    return $role->getThirdPartySetting('farm_role', 'access', FALSE);
  }

  /**
   * {@inheritdoc}
   */
  public function isPermissionInRole($permission, RoleInterface $role) {
    return in_array($permission, $this->getManagedRolePermissions($role));
  }

  /**
   * Helper function to build managed permissions for managed roles.
   *
   * @param \Drupal\user\RoleInterface $role
   *   The role to load permissions for.
   *
   * @return string[]
   *   Array of permissions for the managed role.
   */
  public function getManagedRolePermissions(RoleInterface $role): array {

    // Start list of permissions.
    $perms = [];

    // If the role does not have farm_role settings, bail.
    if (!$this->isManagedRole($role)) {
      return $perms;
    }

    // Load the Role's third party farm_role access settings.
    $access_settings = $role->getThirdPartySetting('farm_role', 'access');

    // Get all plugin definitions.
    $plugin_definitions = $this->getDefinitions();

    // Include permissions defined by plugin_definitions config entities.
    foreach ($plugin_definitions as $plugin_definition) {

      // Create an instance of the plugin.
      $plugin = $this->createInstance($plugin_definition['id']);

      // Always include default permissions.
      $default_perms = $plugin->getDefaultPermissions();
      $perms = array_merge($perms, $default_perms);

      // Include manager permissions if the role has manager access.
      if (!empty($access_settings['manager'])) {
        $manager_perms = $plugin->getManagerPermissions();
        $perms = array_merge($perms, $manager_perms);
      }

      // Include config permissions if the role has config access.
      if (!empty($access_settings['config'])) {
        $config_perms = $plugin->getConfigPermissions();
        $perms = array_merge($perms, $config_perms);
      }

      // Include permissions defined by permission callbacks.
      foreach ($plugin->getPermissionCallbacks() as $permission_callback) {

        // Resolve callback name and call the function. Pass the Role object as
        // a parameter so the callback can access the role's settings.
        $callback = $this->controllerResolver->getControllerFromDefinition($permission_callback);
        if ($callback_permissions = call_user_func($callback, $role)) {

          // Add any callback permissions to the array of permissions.
          $perms = array_merge($perms, $callback_permissions);
        }
      }
    }

    // Load the access.entity settings. Use an empty array if not provided.
    $entity_settings = $access_settings['entity'] ?? [];

    // Managed entity types.
    $managed_entity_types = [
      'asset',
      'data_stream',
      'log',
      'organization',
      'plan',
      'taxonomy_term',
      'quantity',
    ];

    // Start an array of permission rules. This will be a multi-dimensional
    // array that ultimately defines which permission strings will be given to
    // the managed role. Each entity type's operations can be granted to
    // individual bundles or all bundles by providing 'all' as a bundle name.
    // Once built, the array will contain the following structure:
    // $permission_rules[$entity_types][$operations][$bundles];.
    $permission_rules = [];

    // Build permission rules for each entity type.
    foreach ($managed_entity_types as $entity_type) {

      // Create empty array of operations for the entity_type.
      $permission_rules[$entity_type] = [];

      // Different entity types support different operations. Allow each entity
      // type to map the high level 'create_all', 'view all', 'update all' and
      // 'delete_all' operations to their specific operations.
      switch ($entity_type) {

        // Entity types with EntityOwnerTrait and RevisionLogEntityTrait have
        // additional permissions for view, update and delete operations:
        // Owner adds "operation any bundle" or "operation own bundle".
        // Revision adds "view all bundle revisions".
        case 'asset':
        case 'log':
        case 'organization':
        case 'plan':
        case 'quantity':

          // Create.
          if (!empty($entity_settings['create all'])) {
            $permission_rules[$entity_type]['create'] = ['all'];
          }

          // View.
          if (!empty($entity_settings['view all'])) {
            $perms[] = "access $entity_type collection";
            $perms[] = 'view any ' . $entity_type;
            $perms[] = 'view own ' . $entity_type;
            $perms[] = 'view all ' . $entity_type . ' revisions';
            $permission_rules[$entity_type]['view any'] = ['all'];
            $permission_rules[$entity_type]['view own'] = ['all'];
          }

          // Update.
          if (!empty($entity_settings['update all'])) {
            $permission_rules[$entity_type]['update any'] = ['all'];
            $permission_rules[$entity_type]['update own'] = ['all'];
          }

          // Delete.
          if (!empty($entity_settings['delete all'])) {
            $permission_rules[$entity_type]['delete any'] = ['all'];
            $permission_rules[$entity_type]['delete own'] = ['all'];
          }
          break;

        // Entity types with basic CRUD permissions.
        case 'data_stream':

          // Create.
          if (!empty($entity_settings['create all'])) {
            $permission_rules[$entity_type]['create'] = ['all'];
          }

          // View.
          if (!empty($entity_settings['view all'])) {
            $perms[] = 'view ' . $entity_type;
            $permission_rules[$entity_type]['view'] = ['all'];
          }

          // Update.
          if (!empty($entity_settings['update all'])) {
            $permission_rules[$entity_type]['update'] = ['all'];
          }

          // Delete.
          if (!empty($entity_settings['delete all'])) {
            $permission_rules[$entity_type]['delete'] = ['all'];
          }
          break;

        // Taxonomy terms are a unique case for two reasons:
        // View access is determined by the "access content" permission
        // and "edit" is the name for the update operation permission.
        case 'taxonomy_term':

          // Create.
          if (!empty($entity_settings['create all'])) {
            $permission_rules[$entity_type]['create'] = ['all'];
          }

          // Update.
          if (!empty($entity_settings['update all'])) {
            $permission_rules[$entity_type]['edit'] = ['all'];
          }

          // Delete.
          if (!empty($entity_settings['delete all'])) {
            $permission_rules[$entity_type]['delete'] = ['all'];
          }
          break;
      }
    }

    // Include granular entity + bundle permissions if defined on the role.
    if (!empty($entity_settings['type'])) {

      // Recursively merge granular permissions into the permission_rules array.
      $permission_rules = array_merge_recursive(
        $permission_rules,
        $entity_settings['type']
      );
    }

    // Build permissions for each entity type as defined in the
    // permission_rules array.
    foreach ($permission_rules as $entity_type => $operations) {

      // Load all bundles of this entity type.
      $entity_bundle_info = $this->entityTypeBundleInfo->getBundleInfo($entity_type);
      $entity_bundles = array_keys($entity_bundle_info);

      // Build permissions for each operation associated with the entity.
      foreach ($operations as $operation => $allowed_bundles) {

        // Build operation permission for each bundle in the entity.
        foreach ($entity_bundles as $bundle) {

          // Build the operation permission string for each entity type. The
          // permission syntax may be different for each entity type so build
          // permission strings according to the entity type. Only add
          // permissions if the operation explicitly lists the bundle name or
          // specifies 'all' bundles.
          switch ($entity_type) {

            case 'asset':
            case 'log':
            case 'organization':
            case 'plan':
            case 'quantity':
            case 'data_stream':
              if (array_intersect(['all', $bundle], $allowed_bundles)) {
                $perms[] = $operation . ' ' . $bundle . ' ' . $entity_type;
              }
              break;

            case 'taxonomy_term':
              if (array_intersect(['all', $bundle], $allowed_bundles)) {
                $perms[] = $operation . ' terms in ' . $bundle;
              }
              break;
          }
        }
      }
    }

    return $perms;
  }

}
