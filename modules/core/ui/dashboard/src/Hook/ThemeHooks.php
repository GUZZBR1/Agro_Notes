<?php

declare(strict_types=1);

namespace Drupal\farm_ui_dashboard\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;

/**
 * Theme hook implementations for farm_ui_dashboard.
 */
class ThemeHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_toolbar_alter().
   */
  #[Hook('toolbar_alter')]
  public function toolbarAlter(&$items) {

    // Rename home item to "Início".
    if (!empty($items['home'])) {
      $items['home']['tab']['#title'] = $this->t('Início');
    }
  }

}
