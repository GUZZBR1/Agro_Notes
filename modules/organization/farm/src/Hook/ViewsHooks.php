<?php

declare(strict_types=1);

namespace Drupal\farm_farm\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;

/**
 * Hook implementations for farm_farm.
 */
class ViewsHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_views_data_alter().
   */
  #[Hook('views_data_alter')]
  public function viewsDataAlter(array &$data) {

    // Provide a farm_organization_asset argument for views of logs.
    if (isset($data['log_field_data'])) {
      $data['log_field_data']['farm_organization_asset'] = [
        'title' => $this->t('Farm organization asset'),
        'help' => $this->t('Assets that are associated with the farm organization.'),
        'argument' => [
          'id' => 'farm_organization_asset',
        ],
      ];
    }
  }

}
