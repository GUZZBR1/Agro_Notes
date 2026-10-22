<?php

declare(strict_types=1);

namespace Drupal\farm_entity;

use Drupal\Core\DependencyInjection\ContainerBuilder;
use Drupal\Core\DependencyInjection\ServiceProviderBase;

/**
 * Overrides the entity_field.manager service.
 *
 * @deprecated in farm:4.0.2 and is removed from farm:5.0.0. No replacement is
 *   necessary.
 * @see https://www.drupal.org/node/3591108
 */
class FarmEntityServiceProvider extends ServiceProviderBase {

  /**
   * {@inheritdoc}
   */
  public function alter(ContainerBuilder $container) {
    if ($container->hasDefinition('entity_field.manager')) {
      $definition = $container->getDefinition('entity_field.manager');
      $definition->setClass('Drupal\farm_entity\Entity\EntityFieldManager');
    }
  }

}
