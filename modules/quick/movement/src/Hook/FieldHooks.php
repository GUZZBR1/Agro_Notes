<?php

declare(strict_types=1);

namespace Drupal\farm_quick_movement\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;

/**
 * Field hook implementations for farm_quick_movement.
 */
class FieldHooks {

  /**
   * Implements hook_entity_base_field_info_alter().
   */
  #[Hook('entity_base_field_info_alter')]
  public function entityBaseFieldInfoAlter(&$fields, EntityTypeInterface $entity_type) {
    /** @var \Drupal\Core\Field\BaseFieldDefinition[] $fields */

    // Add "Move" button to asset "Current location" field formatter which
    // redirects to the Movement quick form.
    if ($entity_type->id() == 'asset' && !empty($fields['location'])) {
      $display_options = $fields['location']->getDisplayOptions('view');
      $display_options['type'] = 'asset_current_location_move';
      $display_options['settings']['move_asset_button'] = TRUE;
      $fields['location']->setDisplayOptions('view', $display_options);
    }
  }

}
