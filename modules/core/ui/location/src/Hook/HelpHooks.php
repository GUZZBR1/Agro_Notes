<?php

declare(strict_types=1);

namespace Drupal\farm_ui_location\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Routing\RouteMatchInterface;
use Drupal\Core\StringTranslation\StringTranslationTrait;

/**
 * Help hook implementations for farm_ui_location.
 */
class HelpHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_help().
   */
  #[Hook('help')]
  public function help($route_name, RouteMatchInterface $route_match) {
    $output = '';
    // Locations overview help text.
    if ($route_name == 'farm.locations') {
      $output .= '<p>' . $this->t('Locations represent places of interest. They are assets, and assets can be moved to them. Logs can reference them.') . '</p>';
      $output .= '<p>' . $this->t('Locations can be organized into a hierarchy with parent relationships.') . '</p>';
    }
    // Child locations help text.
    if ($route_name == 'farm.asset.locations') {
      $output .= '<p>' . $this->t('This page shows the sub-hierarchy of this location. It includes all location assets that list this location as their parent, as well as all of their children.') . '</p>';
    }
    // Drag and drop help text.
    if (in_array($route_name, [
      'farm.locations',
      'farm.asset.locations',
    ])) {
      $output .= '<p>' . $this->t('To change the hierarchy, either click on individual assets and edit their parent, or click %toggle_button below to enable drag and drop editing on this page. The %save_button button will save changes, and %reset_button will reset them.', [
        '%toggle_button' => $this->t('Toggle drag and drop'),
        '%save_button' => $this->t('Save'),
        '%reset_button' => $this->t('Reset'),
      ]) . '</p>';
    }
    return $output;
  }

}
