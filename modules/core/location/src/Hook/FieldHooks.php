<?php

declare(strict_types=1);

namespace Drupal\farm_location\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_field\FarmFieldFactoryInterface;
use Drupal\farm_location\Field\AssetGeometryItemList;
use Drupal\farm_location\Field\AssetLocationItemList;
use Drupal\farm_location\LocationDefaultValues;

/**
 * Field hook implementations for farm_location.
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

    // Add location base fields to entity types.
    if ($entity_type->id() == 'asset') {
      return $this->assetFields();
    }
    elseif ($entity_type->id() == 'log') {
      return $this->logFields();
    }
    return [];
  }

  /**
   * Implements hook_entity_base_field_info_alter().
   */
  #[Hook('entity_base_field_info_alter')]
  public function entityBaseFieldInfoAlter(&$fields, EntityTypeInterface $entity_type) {
    /** @var \Drupal\field\Entity\FieldConfig[] $fields */

    // Prevent creating circular asset location.
    if ($entity_type->id() == 'log' && !empty($fields['asset'])) {
      $fields['asset']->addConstraint('CircularAssetLocation');
    }
  }

  /**
   * Define asset location base fields.
   *
   * @return array
   *   Returns an array of field information for use with farm_field.factory.
   */
  private function assetFields(): array {
    $fields = [];

    // Current location field.
    // This is computed based on an asset's movements.
    $options = [
      'type' => 'entity_reference',
      'label' => $this->t('Current location'),
      'target_type' => 'asset',
      'multiple' => TRUE,
      'computed' => AssetLocationItemList::class,
      'hidden' => 'form',
      'view_display_options' => [
        'label' => 'inline',
        'type' => 'asset_current_location',
        'settings' => [
          'link' => TRUE,
          'render_without_location' => TRUE,
        ],
        'weight' => 50,
      ],
    ];
    $fields['location'] = $this->farmFieldFactory->baseFieldDefinition($options);

    // Current geometry field.
    // This is computed based on an asset's movements or its intrinsic geometry.
    $options = [
      'type' => 'geofield',
      'label' => $this->t('Current geometry'),
      'computed' => AssetGeometryItemList::class,
      'hidden' => 'form',
      'weight' => [
        'view' => 40,
      ],
    ];
    $fields['geometry'] = $this->farmFieldFactory->baseFieldDefinition($options);

    // Intrinsic geometry field.
    // This is added as a bundle field definition to all asset types rather than
    // a base field definition so that data is stored in a dedicated database
    // table.
    $options = [
      'type' => 'geofield',
      'label' => $this->t('Intrinsic geometry'),
      'description' => $this->t('Add geometry data to this asset to describe its intrinsic location. This will only be used if the asset is fixed.'),
      'weight' => [
        'form' => 50,
      ],
      'hidden' => 'view',
      'populate_file_field' => 'file',
    ];
    $fields['intrinsic_geometry'] = $this->farmFieldFactory->bundleFieldDefinition($options);

    // Location boolean field.
    $options = [
      'type' => 'boolean',
      'label' => $this->t('Is location'),
      'description' => $this->t('If this asset is a location, then other assets can be moved to it.'),
      'default_value_callback' => LocationDefaultValues::class . '::isLocation',
      'weight' => [
        'form' => 0,
      ],
      'view_display_options' => [
        'label' => 'inline',
        'type' => 'hideable_boolean',
        'settings' => [
          'format' => 'default',
          'format_custom_false' => '',
          'format_custom_true' => '',
          'hide_if_false' => TRUE,
        ],
        'weight' => 0,
      ],
    ];
    $fields['is_location'] = $this->farmFieldFactory->baseFieldDefinition($options);

    // Fixed boolean field.
    $options = [
      'type' => 'boolean',
      'label' => $this->t('Is fixed'),
      'description' => $this->t('If this asset is fixed, then it can have an intrinsic geometry. If the asset will move around, then it is not fixed and geometry will be determined by movement logs.'),
      'default_value_callback' => LocationDefaultValues::class . '::isFixed',
      'weight' => [
        'form' => 10,
      ],
      'view_display_options' => [
        'label' => 'inline',
        'type' => 'hideable_boolean',
        'settings' => [
          'format' => 'default',
          'format_custom_false' => '',
          'format_custom_true' => '',
          'hide_if_false' => TRUE,
        ],
        'weight' => 10,
      ],
    ];
    $fields['is_fixed'] = $this->farmFieldFactory->baseFieldDefinition($options);

    return $fields;
  }

  /**
   * Define log location base fields.
   *
   * @return array
   *   Returns an array of field information for use with farm_field.factory.
   */
  private function logFields(): array {
    $fields = [];

    // Location asset reference field.
    $options = [
      'type' => 'entity_reference',
      'label' => $this->t('Location'),
      'description' => $this->t('Where does this take place?'),
      'target_type' => 'asset',
      'multiple' => TRUE,
      'weight' => [
        'form' => 20,
        'view' => 20,
      ],
    ];
    $field = $this->farmFieldFactory->baseFieldDefinition($options);
    $field->setSetting('handler', 'views');
    $field->setSetting('handler_settings', [
      'view' => [
        'view_name' => 'farm_location_reference',
        'display_name' => 'entity_reference',
      ],
    ]);
    $fields['location'] = $field;

    // Geometry field.
    // This is added as a bundle field definition to all log types rather than
    // a base field definition so that data is stored in a dedicated database
    // table.
    $options = [
      'type' => 'geofield',
      'label' => $this->t('Geometry'),
      'description' => $this->t('Add geometry data to this log to describe where it took place.'),
      'weight' => [
        'form' => 20,
        'view' => 20,
      ],
      'populate_file_field' => 'file',
    ];
    $fields['geometry'] = $this->farmFieldFactory->bundleFieldDefinition($options);

    // Movement boolean field.
    $options = [
      'type' => 'boolean',
      'label' => $this->t('Is movement'),
      'description' => $this->t('If this log is a movement, then all assets referenced by it will be located in the referenced locations and/or geometry at the time the log takes place. The log must have a status of "done" in order for the movement to take effect.'),
      'default_value_callback' => LocationDefaultValues::class . '::isMovement',
      'weight' => [
        'form' => 20,
      ],
      'view_display_options' => [
        'label' => 'inline',
        'type' => 'hideable_boolean',
        'settings' => [
          'format' => 'default',
          'format_custom_false' => '',
          'format_custom_true' => '',
          'hide_if_false' => TRUE,
        ],
        'weight' => 20,
      ],
    ];
    $fields['is_movement'] = $this->farmFieldFactory->baseFieldDefinition($options);

    return $fields;
  }

}
