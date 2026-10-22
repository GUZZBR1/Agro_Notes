<?php

declare(strict_types=1);

namespace Drupal\farm_import_csv_test\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_field\FarmFieldFactoryInterface;

/**
 * Field hook implementations for farm_import_csv_test.
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

    // Add base fields to logs.
    if ($entity_type->id() == 'log') {

      // Add a test string base field.
      $options = [
        'type' => 'string',
        'label' => $this->t('Test string'),
      ];
      $fields['test_string'] = $this->farmFieldFactory->baseFieldDefinition($options);

      // Add an excluded test string base field.
      $options = [
        'type' => 'string',
        'label' => $this->t('Excluded test string'),
      ];
      $fields['excluded_test_string'] = $this->farmFieldFactory->baseFieldDefinition($options);
    }

    return $fields;
  }

  /**
   * Implements hook_farm_import_csv_base_fields().
   */
  #[Hook('farm_import_csv_base_fields')]
  public function farmImportCsvBaseFields(string $entity_type) {
    $base_fields = [];

    // Add log base fields to log CSV importers.
    if ($entity_type == 'log') {

      // Add test string base field.
      $base_fields[] = 'test_string';

      // Add excluded test string base field (so that it can be excluded).
      $base_fields[] = 'excluded_test_string';
    }

    return $base_fields;
  }

  /**
   * Implements hook_farm_import_csv_exclude_fields().
   */
  #[Hook('farm_import_csv_exclude_fields')]
  public function farmImportCsvExcludeFields(string $entity_type) {
    $exclude_fields = [];

    // Exclude the excluded_test_string field from log CSV importers.
    if ($entity_type == 'log') {
      $exclude_fields[] = 'excluded_test_string';
    }

    return $exclude_fields;
  }

}
