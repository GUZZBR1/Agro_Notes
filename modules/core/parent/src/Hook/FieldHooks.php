<?php

declare(strict_types=1);

namespace Drupal\farm_parent\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_field\FarmFieldFactoryInterface;

/**
 * Field hook implementations for farm_parent.
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

    // Add parent base field to all asset types.
    if ($entity_type->id() == 'asset') {
      $parent_info = [
        'type' => 'entity_reference',
        'label' => $this->t('Parents'),
        'description' => $this->t('Reference parent assets to create a lineal/hierarchical relationship.'),
        'target_type' => 'asset',
        'multiple' => TRUE,
        'weight' => [
          'form' => 0,
          'view' => 0,
        ],
      ];
      $fields['parent'] = $this->farmFieldFactory->baseFieldDefinition($parent_info);

      // Add entity_reference_validators constraints to parent field.
      // See entity_reference_validators_entity_base_field_info_alter.
      $fields['parent']->addConstraint('CircularReference', [
        'deep' => TRUE,
      ]);
      $fields['parent']->addConstraint('DuplicateReference');
    }

    return $fields;
  }

}
