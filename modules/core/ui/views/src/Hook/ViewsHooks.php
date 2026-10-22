<?php

declare(strict_types=1);

namespace Drupal\farm_ui_views\Hook;

use Drupal\Core\Entity\EntityFieldManagerInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;

/**
 * Views hook implementations for farm_ui_views.
 */
class ViewsHooks {

  use StringTranslationTrait;

  public function __construct(
    protected EntityFieldManagerInterface $entityFieldManager,
  ) {}

  /**
   * Implements hook_views_data_alter().
   */
  #[Hook('views_data_alter')]
  public function viewsDataAlter(array &$data) {

    // Provide an asset_or_location argument for views of logs.
    if (isset($data['log_field_data'])) {
      $data['log_field_data']['asset_or_location'] = [
        'title' => $this->t('Asset or location'),
        'help' => $this->t('Assets that are referenced by the asset or location field on the log.'),
        'argument' => [
          'id' => 'asset_or_location',
        ],
      ];
    }

    // Provide an asset_taxonomy_term_reference argument for views of assets.
    if (isset($data['asset_field_data'])) {
      $data['asset_field_data']['asset_taxonomy_term_reference'] = [
        'title' => $this->t('Asset Taxonomy Term Reference'),
        'help' => $this->t('Taxonomy Terms that are referenced by the asset.'),
        'argument' => [
          'id' => 'entity_taxonomy_term_reference',
        ],
      ];
    }

    // Provide a log_taxonomy_term_reference argument for views of logs.
    if (isset($data['log_field_data'])) {
      $data['log_field_data']['log_taxonomy_term_reference'] = [
        'title' => $this->t('Log Taxonomy Term Reference'),
        'help' => $this->t('Taxonomy Terms that are referenced by the log.'),
        'argument' => [
          'id' => 'entity_taxonomy_term_reference',
        ],
      ];
    }
  }

}
