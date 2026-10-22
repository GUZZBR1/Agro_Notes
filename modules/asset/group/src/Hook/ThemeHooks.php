<?php

declare(strict_types=1);

namespace Drupal\farm_group\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;

/**
 * Theme hook implementations for farm_group.
 */
class ThemeHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_farm_ui_theme_region_items().
   */
  #[Hook('farm_ui_theme_region_items')]
  public function farmUiThemeRegionItems(string $entity_type) {
    $region_items = [];
    if ($entity_type == 'asset') {
      $region_items = [
        'top' => [],
        'first' => [],
        'second' => [
          'group',
        ],
        'bottom' => [],
      ];
    }
    elseif ($entity_type == 'log') {
      $region_items = [
        'top' => [],
        'first' => [],
        'second' => [
          'is_group_assignment',
        ],
        'bottom' => [],
      ];
    }
    return $region_items;
  }

  /**
   * Implements hook_farm_ui_theme_field_groups().
   */
  #[Hook('farm_ui_theme_field_groups')]
  public function farmUiThemeFieldGroups(string $entity_type, string $bundle) {

    // Add a field group for group membership fields on logs.
    if ($entity_type == 'log') {
      return [
        'group' => [
          'location' => 'main',
          'title' => $this->t('Group'),
          'weight' => 60,
        ],
      ];
    }
    return [];
  }

  /**
   * Implements hook_farm_ui_theme_field_group_items().
   */
  #[Hook('farm_ui_theme_field_group_items')]
  public function farmUiThemeFieldGroupItems(string $entity_type, string $bundle) {
    if ($entity_type == 'log') {
      return [
        'group' => 'group',
        'is_group_assignment' => 'group',
      ];
    }
    return [];
  }

}
