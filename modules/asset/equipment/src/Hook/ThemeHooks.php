<?php

declare(strict_types=1);

namespace Drupal\farm_equipment\Hook;

use Drupal\Core\Hook\Attribute\Hook;

/**
 * Theme hook implementations for farm_equipment.
 */
class ThemeHooks {

  /**
   * Implements hook_farm_ui_theme_field_group_items().
   */
  #[Hook('farm_ui_theme_field_group_items')]
  public function farmUiThemeFieldGroupItems(string $entity_type, string $bundle) {
    if ($entity_type == 'log') {
      return [
        'equipment' => 'asset',
      ];
    }
    return [];
  }

}
