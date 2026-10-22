<?php

declare(strict_types=1);

namespace Drupal\farm_flag\Hook;

use Drupal\Core\Hook\Attribute\Hook;

/**
 * Theme hook implementations for farm_flag.
 */
class ThemeHooks {

  /**
   * Implements hook_farm_ui_theme_region_items().
   */
  #[Hook('farm_ui_theme_region_items')]
  public function farmUiThemeRegionItems(string $entity_type) {
    if (in_array($entity_type, ['asset', 'log', 'plan'])) {
      return [
        'second' => [
          'flag',
        ],
      ];
    }
    return [];
  }

  /**
   * Implements hook_theme().
   */
  #[Hook('theme')]
  public function theme() {
    return [
      'field__flag' => [
        'base hook' => 'field',
      ],
    ];
  }

  /**
   * Implements hook_preproces_HOOK().
   */
  #[Hook('preprocess_field__flag')]
  public function preprocessFieldFlag(array &$variables) {

    // Preprocess list_string flag fields.
    if ($variables['element']['#field_type'] == 'list_string') {

      /** @var \Drupal\Core\Field\FieldItemListInterface $items */
      $items = $variables['element']['#items'];

      // Add classes to each flag.
      foreach ($items as $key => $list_item) {
        $classes = ['flag', 'flag--' . $list_item->getString()];
        $variables['items'][$key]['attributes']->addClass($classes);
      }
    }
  }

}
