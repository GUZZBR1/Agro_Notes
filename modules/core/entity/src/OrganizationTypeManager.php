<?php

declare(strict_types=1);

namespace Drupal\farm_entity;

use Drupal\Component\Plugin\Exception\PluginException;
use Drupal\Core\Cache\CacheBackendInterface;
use Drupal\Core\Extension\ModuleHandlerInterface;
use Drupal\Core\Plugin\DefaultPluginManager;
use Drupal\farm_entity\Attribute\OrganizationType;
use Drupal\farm_entity\Plugin\Organization\OrganizationType\OrganizationTypeInterface;

/**
 * Manages discovery and instantiation of organization type plugins.
 *
 * @see \Drupal\farm_entity\Annotation\OrganizationType
 * @see plugin_api
 */
class OrganizationTypeManager extends DefaultPluginManager {

  public function __construct(
    \Traversable $namespaces,
    CacheBackendInterface $cache_backend,
    ModuleHandlerInterface $module_handler,
  ) {
    parent::__construct(
      'Plugin/Organization/OrganizationType',
      $namespaces,
      $module_handler,
      OrganizationTypeInterface::class,
      OrganizationType::class
    );
    $this->alterInfo('organization_type_info');
    $this->setCacheBackend($cache_backend, 'organization_type_plugins');
  }

  /**
   * {@inheritdoc}
   */
  public function processDefinition(&$definition, $plugin_id) {
    parent::processDefinition($definition, $plugin_id);

    foreach (['id', 'label'] as $required_property) {
      if (empty($definition[$required_property])) {
        throw new PluginException(sprintf('The organization type %s must define the %s property.', $plugin_id, $required_property));
      }
    }
  }

}
