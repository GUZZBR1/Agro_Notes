<?php

declare(strict_types=1);

namespace Drupal\farm_input\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\views\ViewExecutable;

/**
 * Views execution hook implementations for farm_input.
 */
class ViewsExecutionHooks {

  use StringTranslationTrait;

  /**
   * Implements hook_views_pre_view().
   */
  #[Hook('views_pre_view')]
  public function viewsPreView(ViewExecutable $view, $display_id, array &$args) {

    // Alter the farm_log View.
    if ($view->id() == 'farm_log') {

      // Only alter the page_type and page_asset displays.
      if (!in_array($display_id, [
        'page_type',
        'page_asset',
      ])) {
        return;
      }

      // Bail if not a view of input logs.
      if (!in_array('input', $args)) {
        return;
      }

      // Add a filter for the quantity material type.
      $table = 'log_field_data';
      $field = 'quantity_material_type';
      $filter_options = [
        'id' => 'material_type_target_id',
        'table' => $table,
        'field' => $field,
        'exposed' => TRUE,
        'expose' => [
          'label' => $this->t('Material type'),
          'identifier' => $field,
          'multiple' => TRUE,
        ],
        'type' => 'select',
        'limit' => TRUE,
      ];
      $view->addHandler($display_id, 'filter', $table, $field, $filter_options);
    }
  }

}
