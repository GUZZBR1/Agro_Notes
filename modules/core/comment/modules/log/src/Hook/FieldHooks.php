<?php

declare(strict_types=1);

namespace Drupal\farm_comment_log\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\farm_comment\FarmCommentHelper;

/**
 * Field hoook implementations for farm_comment_log.
 */
class FieldHooks {

  /**
   * Implements hook_entity_base_field_info().
   */
  #[Hook('entity_base_field_info')]
  public function entityBaseFieldInfo(EntityTypeInterface $entity_type) {
    $fields = [];

    // Add comment base field to logs.
    if ($entity_type->id() == 'log') {
      $fields['comment'] = FarmCommentHelper::commentBaseFieldDefinition('log');
    }

    return $fields;
  }

}
