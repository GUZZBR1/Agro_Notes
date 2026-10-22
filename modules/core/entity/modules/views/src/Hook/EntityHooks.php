<?php

declare(strict_types=1);

namespace Drupal\farm_entity_views\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\farm_entity_views\FarmEntityViewsData;
use Drupal\farm_entity_views\FarmLogViewsData;
use Drupal\farm_entity_views\FarmQuantityViewsData;

/**
 * Entity hook implementations for farm_entity_views.
 */
class EntityHooks {

  /**
   * Implements hook_entity_type_build().
   */
  #[Hook('entity_type_build')]
  public function entityTypeBuild(array &$entity_types) {

    // Set the views data handler class to FarmEntityViewsData.
    foreach (['asset', 'log', 'organization', 'plan', 'plan_record', 'quantity'] as $entity_type) {
      if (!empty($entity_types[$entity_type])) {

        // Use the correct class for each entity type.
        // Logs and quantities provide their own that we must extend from.
        $views_data_class = FarmEntityViewsData::class;
        switch ($entity_type) {
          case 'log':
            $views_data_class = FarmLogViewsData::class;
            break;

          case 'quantity':
            $views_data_class = FarmQuantityViewsData::class;
            break;
        }
        $entity_types[$entity_type]->setHandlerClass('views_data', $views_data_class);
      }
    }
  }

}
