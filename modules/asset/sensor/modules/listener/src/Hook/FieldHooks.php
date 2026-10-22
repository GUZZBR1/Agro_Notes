<?php

declare(strict_types=1);

namespace Drupal\farm_sensor_listener\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\data_stream\Entity\DataStream;
use Drupal\farm_field\FarmFieldFactoryInterface;

/**
 * Field hook implementations for farm_sensor_listener.
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

    // Add a public_key reference field to sensor assets.
    if ($entity_type->id() === 'asset' && $bundle === 'sensor') {
      $options = [
        'type' => 'string',
        'label' => $this->t('Public key (legacy)'),
        'description' => $this->t('Public key (legacy) for the sensor.'),
        'default_value_callback' => DataStream::class . '::createUniqueKey',
        'weight' => [
          'form' => 3,
        ],
      ];
      $fields['public_key'] = $this->farmFieldFactory->bundleFieldDefinition($options);
    }

    return $fields;
  }

}
