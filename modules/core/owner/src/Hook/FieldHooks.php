<?php

declare(strict_types=1);

namespace Drupal\farm_owner\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_field\FarmFieldFactoryInterface;

/**
 * Field hook implementations for farm_owner.
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

    // Add owner field to logs, assets, and plans.
    if (in_array($entity_type->id(), [
      'asset',
      'log',
      'plan',
    ])) {
      $field_info = [
        'type' => 'entity_reference',
        'label' => $this->t('Owners'),
        'description' => $this->t('Assign ownership to one or more users.'),
        'target_type' => 'user',
        'multiple' => TRUE,
        'weight' => [
          'form' => -70,
          'view' => -70,
        ],
      ];
      $fields['owner'] = $this->farmFieldFactory->baseFieldDefinition($field_info);
    }

    return $fields;
  }

}
