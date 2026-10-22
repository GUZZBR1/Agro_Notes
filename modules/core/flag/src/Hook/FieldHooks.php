<?php

declare(strict_types=1);

namespace Drupal\farm_flag\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_field\FarmFieldFactoryInterface;
use Drupal\farm_flag\FarmFlagHelper;

/**
 * Field hook implementations for farm_flag.
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

    // Add flag field to farmOS entities.
    if (in_array($entity_type->id(), ['asset', 'log', 'plan'])) {
      $field_info = [
        'type' => 'list_string',
        'label' => $this->t('Flags'),
        'description' => $this->t('Add flags to enable better sorting and filtering of records.'),
        'allowed_values_function' => [FarmFlagHelper::class, 'flagAllowedValues'],
        'multiple' => TRUE,
        'weight' => [
          'form' => -75,
          'view' => -75,
        ],
      ];
      $fields['flag'] = $this->farmFieldFactory->baseFieldDefinition($field_info);
    }

    return $fields;
  }

}
