<?php

declare(strict_types=1);

namespace Drupal\farm_entity;

use Drupal\Component\Plugin\Exception\PluginException;
use Drupal\Core\Cache\CacheBackendInterface;
use Drupal\Core\Extension\ModuleHandlerInterface;
use Drupal\Core\Plugin\DefaultPluginManager;
use Drupal\farm_entity\Attribute\QuantityType;
use Drupal\farm_entity\Plugin\Quantity\QuantityType\QuantityTypeInterface;

/**
 * Quantity Type plugin manager.
 */
class QuantityTypeManager extends DefaultPluginManager {

  public function __construct(
    \Traversable $namespaces,
    CacheBackendInterface $cache_backend,
    ModuleHandlerInterface $module_handler,
  ) {
    parent::__construct(
      'Plugin/Quantity/QuantityType',
      $namespaces,
      $module_handler,
      QuantityTypeInterface::class,
      QuantityType::class,
      'Drupal\farm_entity\Annotation\QuantityType',
    );
    $this->alterInfo('quantity_type_info');
    $this->setCacheBackend($cache_backend, 'quantity_type_plugins');
  }

  /**
   * {@inheritdoc}
   */
  public function processDefinition(&$definition, $plugin_id) {
    parent::processDefinition($definition, $plugin_id);

    foreach (['id', 'label'] as $required_property) {
      if (empty($definition[$required_property])) {
        throw new PluginException(sprintf('The quantity type %s must define the %s property.', $plugin_id, $required_property));
      }
    }
  }

}
