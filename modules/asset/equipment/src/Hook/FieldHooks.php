<?php

declare(strict_types=1);

namespace Drupal\farm_equipment\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_field\FarmFieldFactoryInterface;

/**
 * Field hook implementations for farm_equipment.
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

    // Add an Equipment reference field to logs.
    if ($entity_type->id() == 'log') {
      $options = [
        'type' => 'entity_reference',
        'label' => $this->t('Equipment used'),
        'description' => $this->t('What equipment was used?'),
        'target_type' => 'asset',
        'target_bundle' => 'equipment',
        'multiple' => TRUE,
        'weight' => [
          'form' => 40,
          'view' => 40,
        ],
      ];
      $fields['equipment'] = $this->farmFieldFactory->baseFieldDefinition($options);
    }

    return $fields;
  }

  /**
   * Implements hook_farm_import_csv_base_fields().
   */
  #[Hook('farm_import_csv_base_fields')]
  public function farmImportCsvBaseFields(string $entity_type) {
    $base_fields = [];

    // Add equipment base field to log CSV importers.
    if ($entity_type == 'log') {
      $base_fields[] = 'equipment';
    }

    return $base_fields;
  }

  /**
   * Implements hook_farm_ui_views_base_fields().
   */
  #[Hook('farm_ui_views_base_fields')]
  public function farmUiViewsBaseFields(string $entity_type) {
    $base_fields = [];

    // Add equipment base field to farmOS log Views.
    if ($entity_type == 'log') {
      $base_fields[] = 'equipment';
    }

    return $base_fields;
  }

}
