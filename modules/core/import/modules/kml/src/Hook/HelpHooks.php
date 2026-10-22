<?php

declare(strict_types=1);

namespace Drupal\farm_import_kml\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Routing\RouteMatchInterface;
use Drupal\Core\StringTranslation\StringTranslationTrait;

/**
 * Help hook implementations for farm_import_kml.
 */
class HelpHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_help().
   */
  #[Hook('help')]
  public function help($route_name, RouteMatchInterface $route_match) {
    $output = '';

    // KML importer.
    if ($route_name == 'farm.import.kml') {
      $output .= '<p>' . $this->t('This KML importer will create multiple Land assets from a single KML file. Select the KML file you would like to upload, as well as the default land type, then click "Parse".') . '</p>';
    }

    return $output;
  }

}
