<?php

declare(strict_types=1);

namespace Drupal\farm_farm\Hook;

use Drupal\Core\Hook\Attribute\Hook;

/**
 * Theme hook implementations for farm_farm.
 */
class ThemeHooks {

  /**
   * Implements hook_farm_ui_theme_field_group_items().
   */
  #[Hook('farm_ui_theme_field_group_items')]
  public function farmUiThemeFieldGroupItems(string $entity_type, string $bundle) {
    if ($entity_type == 'asset') {
      return [
        'farm' => 'meta',
      ];
    }
    return [];
  }

  /**
   * Implements hook_farm_ui_theme_region_items().
   */
  #[Hook('farm_ui_theme_region_items')]
  public function farmUiThemeRegionItems(string $entity_type) {
    if ($entity_type == 'asset') {
      return [
        'second' => [
          'farm',
        ],
      ];
    }
    return [];
  }

}
