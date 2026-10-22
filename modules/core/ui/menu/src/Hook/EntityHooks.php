<?php

declare(strict_types=1);

namespace Drupal\farm_ui_menu\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\farm_ui_menu\Menu\DefaultSecondaryLocalTaskProvider;

/**
 * Entity hook implementations for farm_ui_menu.
 */
class EntityHooks {

  /**
   * Implements hook_entity_type_build().
   */
  #[Hook('entity_type_build')]
  public function entityTypeBuild(array &$entity_types) {

    // Override the default local task provider to use secondary tasks.
    $target_entity_types = [
      'asset',
      'data_stream',
      'log',
      'organization',
      'plan',
      'taxonomy_term',
    ];
    foreach ($target_entity_types as $entity_type) {
      if (isset($entity_types[$entity_type])) {
        $handlers = $entity_types[$entity_type]->getHandlerClasses();
        $handlers['local_task_provider']['default'] = DefaultSecondaryLocalTaskProvider::class;
        $entity_types[$entity_type]->setHandlerClass('local_task_provider', $handlers['local_task_provider']);
      }
    }
  }

}
