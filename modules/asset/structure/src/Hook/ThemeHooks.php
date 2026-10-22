<?php

declare(strict_types=1);

namespace Drupal\farm_structure\Hook;

use Drupal\Core\Hook\Attribute\Hook;

/**
 * Theme hook implementations for farm_structure.
 */
class ThemeHooks {

  /**
   * Implements hook_farm_ui_theme_region_items().
   */
  #[Hook('farm_ui_theme_region_items')]
  public function farmUiThemeRegionItems(string $entity_type) {
    if ($entity_type == 'asset') {
      return [
        'second' => [
          'structure_type',
        ],
      ];
    }
    return [];
  }

}
