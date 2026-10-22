<?php

declare(strict_types=1);

namespace Drupal\farm_ui_dashboard_test\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;

/**
 * Theme hook implementations for farm_ui_dashboard_test.
 */
class ThemeHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_farm_dashboard_panes().
   */
  #[Hook('farm_dashboard_panes')]
  public function farmDashboardPanes() {
    return [
      'dashboard_block' => [
        'title' => $this->t('Test block title'),
        'block' => 'dashboard_test_block',
      ],
      'dashboard_view' => [
        'view' => 'dashboard_test_view',
        'view_display_id' => 'user_list',
      ],
      'dashboard_map' => [
        'title' => $this->t('Dashboard map placeholder'),
        'block' => 'dashboard_test_block',
        'region' => 'top',
      ],
    ];
  }

}
