<?php

declare(strict_types=1);

namespace Drupal\farm_l10n\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Routing\RouteMatchInterface;
use Drupal\Core\StringTranslation\StringTranslationTrait;

/**
 * Help hook implementations for farm_l10n.
 */
class HelpHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_help().
   */
  #[Hook('help')]
  public function help($route_name, RouteMatchInterface $route_match) {
    $output = '';

    // Help text for the farm/settings/language form.
    if ($route_name == 'farm_l10n.settings') {
      $output .= '<p>' . $this->t('Select the default language for the user interface. Individual users can override this by editing their profile.') . '</p>';
    }

    return $output;
  }

}
