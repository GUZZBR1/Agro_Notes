<?php

declare(strict_types=1);

namespace Drupal\farm_id_tag\Hook;

use Drupal\Core\Hook\Attribute\Hook;

/**
 * Theme hook implementations for farm_id_tag.
 */
class ThemeHooks {

  /**
   * Implements hook_theme().
   */
  #[Hook('theme')]
  public function theme() {
    return [
      'field__id_tag' => [
        'template' => 'field--id-tag',
        'base hook' => 'field',
      ],
    ];
  }

}
