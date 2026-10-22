<?php

declare(strict_types=1);

namespace Drupal\farm_quick\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_field\FarmFieldFactoryInterface;

/**
 * Field hook implementations for farm_quick.
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

    // We only act on asset and log entities.
    if (!in_array($entity_type->id(), [
      'asset',
      'log',
    ])) {
      return $fields;
    }

    // Add a hidden quick form field.
    $options = [
      'type' => 'string',
      'label' => $this->t('Quick form'),
      'description' => $this->t('References the quick form that was used to create this record.'),
      'multiple' => TRUE,
      'hidden' => TRUE,
    ];
    $fields['quick'] = $this->farmFieldFactory->baseFieldDefinition($options);

    return $fields;
  }

}
