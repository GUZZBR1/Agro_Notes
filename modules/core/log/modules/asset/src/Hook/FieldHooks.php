<?php

declare(strict_types=1);

namespace Drupal\farm_log_asset\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_field\FarmFieldFactoryInterface;

/**
 * Field hook implementations for farm_log_asset.
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

    // Add an asset reference field to logs.
    $field_info = [
      'type' => 'entity_reference',
      'label' => $this->t('Assets'),
      'description' => $this->t('What assets do this log pertain to?'),
      'target_type' => 'asset',
      'multiple' => TRUE,
      'weight' => [
        'form' => 0,
        'view' => 0,
      ],
    ];
    $fields['asset'] = $this->farmFieldFactory->baseFieldDefinition($field_info);

    return $fields;
  }

}
