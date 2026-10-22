<?php

declare(strict_types=1);

namespace Drupal\farm_group\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;

/**
 * Views hook implementations for farm_group.
 */
class ViewsHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_views_data_alter().
   */
  #[Hook('views_data_alter')]
  public function viewsDataAlter(array &$data) {
    // Add the computed group membership field to assets.
    $data['asset']['group'] = [
      'title' => $this->t('Current group'),
      'field' => [
        'id' => 'asset_group',
        'field_name' => 'group',
      ],
      'argument' => [
        'id' => 'asset_group',
      ],
    ];
  }

}
