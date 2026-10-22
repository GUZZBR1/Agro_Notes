<?php

declare(strict_types=1);

namespace Drupal\farm_entity_test\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_field\FarmFieldFactoryInterface;

/**
 * Field hook implementations for farm_entity_test.
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

    // Add a new base field to all logs.
    if ($entity_type->id() == 'log') {
      $options = [
        'type' => 'string',
        'label' => $this->t('Test hook base field'),
      ];
      $fields['test_hook_base_field'] = $this->farmFieldFactory->baseFieldDefinition($options);
    }

    return $fields;
  }

  /**
   * Implements hook_farm_entity_bundle_field_info().
   */
  #[Hook('farm_entity_bundle_field_info')]
  public function farmEntityBundleFieldInfo(EntityTypeInterface $entity_type, string $bundle) {
    $fields = [];

    // Add a new bundle field to test logs.
    if ($entity_type->id() == 'log' && in_array($bundle, ['test', 'test_override'])) {
      $options = [
        'type' => 'string',
        'label' => $this->t('Test hook bundle field'),
      ];
      $fields['test_hook_bundle_field'] = $this->farmFieldFactory->bundleFieldDefinition($options);
    }

    // Add bundle specific fields to all log types.
    if ($entity_type->id() == 'log') {
      $options = [
        'type' => 'string',
        'label' => $this->t('Test bundle specific field for: @bundle', [
          '@bundle' => $bundle,
        ]),
      ];
      $field_name = 'test_hook_bundle_' . $bundle . '_specific_field';
      $fields[$field_name] = $this->farmFieldFactory->bundleFieldDefinition($options);
    }

    return $fields;
  }

}
