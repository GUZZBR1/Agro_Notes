<?php

declare(strict_types=1);

namespace Drupal\farm_location\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;

/**
 * Views hook implementations for farm_location.
 */
class ViewsHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_views_data_alter().
   */
  #[Hook('views_data_alter')]
  public function viewsDataAlter(array &$data) {

    // Add computed fields to assets.
    if (isset($data['asset'])) {

      // Computed geometry.
      $data['asset']['geometry'] = [
        'title' => $this->t('Geometry'),
        'field' => [
          'id' => 'asset_geometry',
          'field_name' => 'geometry',
        ],
      ];

      // Computed location.
      $data['asset']['location'] = [
        'title' => $this->t('Current location'),
        'field' => [
          'id' => 'asset_location',
          'field_name' => 'location',
        ],
        'argument' => [
          'id' => 'asset_location',
        ],
      ];
    }
  }

}
