<?php

declare(strict_types=1);

namespace Drupal\farm_comment_plan\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\farm_comment\FarmCommentHelper;

/**
 * Field hook implementations for farm_comment_plan.
 */
class FieldHooks {

  /**
   * Implements hook_entity_base_field_info().
   */
  #[Hook('entity_base_field_info')]
  public function entityBaseFieldInfo(EntityTypeInterface $entity_type) {
    $fields = [];

    // Add comment base field to plans.
    if ($entity_type->id() == 'plan') {
      $fields['comment'] = FarmCommentHelper::commentBaseFieldDefinition('plan');
    }

    return $fields;
  }

}
