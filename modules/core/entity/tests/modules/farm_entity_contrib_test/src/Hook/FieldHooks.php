<?php

declare(strict_types=1);

namespace Drupal\farm_entity_contrib_test\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_field\FarmFieldFactoryInterface;

/**
 * Field hook implementations for farm_entity_contrib_test.
 */
class FieldHooks {

  use StringTranslationTrait;

  public function __construct(
    protected FarmFieldFactoryInterface $farmFieldFactory,
  ) {}

  /**
   * Implements hook_farm_entity_bundle_field_info().
   */
  #[Hook('farm_entity_bundle_field_info')]
  public function farmEntityBundleFieldInfo(EntityTypeInterface $entity_type, string $bundle) {
    $fields = [];

    // Add a new bundle field to test logs.
    if ($entity_type->id() == 'log' && in_array($bundle, ['test'])) {
      $options = [
        'type' => 'string',
        'label' => $this->t('Test hook bundle field'),
      ];
      $fields['test_contrib_hook_bundle_field'] = $this->farmFieldFactory->bundleFieldDefinition($options);
    }

    return $fields;
  }

}
