<?php

declare(strict_types=1);

namespace Drupal\farm_log_quantity\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_field\FarmFieldFactoryInterface;

/**
 * Field hook implementations for farm_log_quantity.
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

    // We only care about log entities.
    if ($entity_type->id() != 'log') {
      return [];
    }

    // Add a quantity reference field to logs.
    $field_info = [
      'quantity' => [
        'type' => 'entity_reference_revisions',
        'label' => $this->t('Quantity'),
        'description' => $this->t('Add quantity measurements to this log.'),
        'target_type' => 'quantity',
        'multiple' => TRUE,
        'weight' => [
          'form' => 0,
          'view' => 50,
        ],
      ],
    ];
    $fields = [];
    foreach ($field_info as $name => $info) {
      $fields[$name] = $this->farmFieldFactory->baseFieldDefinition($info);
    }

    return $fields;
  }

}
