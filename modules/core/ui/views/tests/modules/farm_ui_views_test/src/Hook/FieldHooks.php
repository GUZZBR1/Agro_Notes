<?php

declare(strict_types=1);

namespace Drupal\farm_ui_views_test\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_field\FarmFieldFactoryInterface;

/**
 * Field hook implementations for farm_ui_views_test.
 */
class FieldHooks {

  use StringTranslationTrait;

  public function __construct(
    protected FarmFieldFactoryInterface $farmFieldFactory,
  ) {}

  /**
   * Implements hook_entity_base_field_info().
   */
  #[Hook('entity_base_field_info')]
  public function entityBaseFieldInfo(EntityTypeInterface $entity_type) {
    $fields = [];

    // Add a test string base field to logs.
    if ($entity_type->id() == 'log') {
      $options = [
        'type' => 'string',
        'label' => $this->t('Test string'),
      ];
      $fields['test_string'] = $this->farmFieldFactory->baseFieldDefinition($options);
    }
    return $fields;
  }

  /**
   * Implements hook_farm_ui_views_base_fields().
   */
  #[Hook('farm_ui_views_base_fields')]
  public function farmUiViewsBaseFields(string $entity_type) {
    $base_fields = [];

    // Add test string base field to farmOS log Views.
    if ($entity_type == 'log') {
      $base_fields[] = 'test_string';
    }
    return $base_fields;
  }

}
