<?php

declare(strict_types=1);

namespace Drupal\farm_pt_br\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Language\LanguageInterface;

/**
 * Theme hook implementations for farmOS localization.
 */
class ThemeHooks {

  /**
   * Implements hook_preprocess_html().
   */
  #[Hook('preprocess_html')]
  public function preprocessHtml(array &$variables): void {
    if (\Drupal::languageManager()->getCurrentLanguage(LanguageInterface::TYPE_INTERFACE)->getId() === 'pt-br') {
      $variables['html_attributes']->setAttribute('lang', 'pt-BR');
    }
  }

}
