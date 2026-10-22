<?php

declare(strict_types=1);

namespace Drupal\farm_ui_views\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;

/**
 * Field hook implementations for farm_ui_views.
 */
class FieldHooks {

  /**
   * Implements hook_entity_base_field_info_alter().
   */
  #[Hook('entity_base_field_info_alter')]
  public function entityBaseFieldInfoAlter(&$fields, EntityTypeInterface $entity_type) {

    // Use Entity Browser widget for certain asset reference fields.
    $alter_fields = [
      'log' => [
        'asset',
      ],
      'quantity' => [
        'inventory_asset',
      ],
    ];
    foreach ($alter_fields as $entity_type_id => $field_names) {
      if ($entity_type->id() != $entity_type_id) {
        continue;
      }
      foreach ($field_names as $field_name) {
        if (!empty($fields[$field_name])) {
          /** @var \Drupal\Core\Field\BaseFieldDefinition[] $fields */
          $form_display_options = $fields[$field_name]->getDisplayOptions('form');
          $form_display_options['type'] = 'entity_browser_entity_reference';
          $form_display_options['settings'] = [
            'entity_browser' => 'farm_asset',
            'field_widget_display' => 'label',
            'field_widget_remove' => TRUE,
            'open' => TRUE,
            'selection_mode' => 'selection_append',
            'field_widget_edit' => FALSE,
            'field_widget_replace' => FALSE,
            'field_widget_display_settings' => [],
          ];
          $fields[$field_name]->setDisplayOptions('form', $form_display_options);
        }
      }
    }
  }

}
