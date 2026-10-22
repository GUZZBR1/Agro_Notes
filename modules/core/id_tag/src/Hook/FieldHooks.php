<?php

declare(strict_types=1);

namespace Drupal\farm_id_tag\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_field\FarmFieldFactoryInterface;

/**
 * Field hook implementations for farm_id_tag.
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

    // Add ID tag field to assets.
    if ($entity_type->id() == 'asset') {
      $field_info = [
        'type' => 'id_tag',
        'label' => $this->t('ID tags'),
        'description' => $this->t('List any identification tags that this asset has. Use the fields below to describe the type, location, and ID of each.'),
        'multiple' => TRUE,
        'weight' => [
          'form' => 20,
          'view' => 20,
        ],
      ];
      $fields['id_tag'] = $this->farmFieldFactory->baseFieldDefinition($field_info);

      // Add an ID tag type constraint to ID tag fields to ensure valid type.
      $fields['id_tag']->addConstraint('IdTagType');
    }

    return $fields;
  }

}
