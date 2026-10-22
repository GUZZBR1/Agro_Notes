<?php

declare(strict_types=1);

namespace Drupal\farm_ui_theme;

use Drupal\Core\Entity\FieldableEntityInterface;

/**
 * Helper methods for farm_ui_theme.
 */
class FarmUiThemeHelper {

  /**
   * Adds a warning message to entities that are archived.
   *
   * @param \Drupal\Core\Entity\FieldableEntityInterface $entity
   *   The entity.
   */
  public static function setArchivedMessage(FieldableEntityInterface $entity) {
    if ($entity->get('archived')->value) {
      \Drupal::messenger()->addWarning(t('This @entity_type is archived. Archived @entity_types should only be edited if they need corrections.', ['@entity_type' => strtolower($entity->getEntityType()->getLabel()->render()), '@entity_types' => strtolower($entity->getEntityType()->getPluralLabel()->render())]));
    }
  }

  /**
   * Splits content into a stacked two-column layout.
   *
   * @param array $variables
   *   A $variables array that contains a 'content' item, which will be replaced
   *   by a stacked two-column layout.
   * @param string $entity_type
   *   The entity type.
   */
  public static function buildStackedTwocolLayout(array &$variables, string $entity_type) {

    // Ask modules for a list of region items.
    $region_items = \Drupal::moduleHandler()->invokeAll('farm_ui_theme_region_items', [$entity_type]);

    // Split the content items into regions.
    $regions = [];
    foreach ($variables['content'] as $index => $item) {
      $region = 'first';
      foreach ($region_items as $region_name => $items) {
        if (in_array($index, $items)) {
          $region = $region_name;
          break;
        }
      }
      $regions[$region][$index] = $item;
    }

    // Build the layout.
    /** @var \Drupal\Core\Layout\LayoutInterface $layout */
    $layout = \Drupal::service('plugin.manager.core.layout')->createInstance('layout_twocol', []);
    $variables['content'] = $layout->build($regions);
  }

}
