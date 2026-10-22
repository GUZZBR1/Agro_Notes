<?php

declare(strict_types=1);

namespace Drupal\farm_group\Hook;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\farm_field\FarmFieldFactoryInterface;
use Drupal\farm_group\Field\AssetGroupItemList;

/**
 * Field hook implementations for farm_group.
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

    // Add group base fields to entity types.
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

    // Prevent creating circular group memberships.
    if ($entity_type->id() == 'log' && !empty($fields['asset'])) {
      $fields['asset']->addConstraint('CircularGroupMembership');
    }
  }

  /**
   * Implements hook_farm_import_csv_base_fields().
   */
  #[Hook('farm_import_csv_base_fields')]
  public function farmImportCsvBaseFields(string $entity_type) {
    $base_fields = [];

    // Add group and is_group_assignment base fields to log CSV importers.
    if ($entity_type == 'log') {
      $base_fields[] = 'group';
      $base_fields[] = 'is_group_assignment';
    }

    return $base_fields;
  }

  /**
   * Implements hook_farm_ui_views_base_fields().
   */
  #[Hook('farm_ui_views_base_fields')]
  public function farmUiViewsBaseFields(string $entity_type) {
    $base_fields = [];

    // Add group base field to farmOS asset and log Views.
    if (in_array($entity_type, ['asset', 'log'])) {
      $base_fields[] = 'group';
    }

    // Add is_group_assignment base field to log Views.
    if ($entity_type == 'log') {
      $base_fields[] = 'is_group_assignment';
    }

    return $base_fields;
  }

  /**
   * Define asset location base fields.
   *
   * @return array
   *   Returns an array of field information for use with farm_field.factory.
   */
  private function assetFields(): array {
    $fields = [];

    // Group membership field.
    // This is computed based on an asset's group assignment logs.
    $options = [
      'type' => 'entity_reference',
      'label' => $this->t('Group membership'),
      'target_type' => 'asset',
      'target_bundle' => 'group',
      'multiple' => TRUE,
      'computed' => AssetGroupItemList::class,
      'hidden' => 'form',
      'weight' => [
        'view' => 94,
      ],
    ];
    $fields['group'] = $this->farmFieldFactory->baseFieldDefinition($options);

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

    // "Is group assignment" boolean field.
    $options = [
      'type' => 'boolean',
      'label' => $this->t('Is group assignment'),
      'description' => $this->t('If this log is a group assignment, any referenced assets will become members of the groups referenced below.'),
      'weight' => [
        'form' => 30,
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
        'weight' => 30,
      ],
    ];
    $fields['is_group_assignment'] = $this->farmFieldFactory->baseFieldDefinition($options);

    // Group reference field.
    $options = [
      'type' => 'entity_reference',
      'label' => $this->t('Groups'),
      'description' => $this->t('If this is a group assignment log, which groups should the referenced assets be assigned to?'),
      'target_type' => 'asset',
      'target_bundle' => 'group',
      'multiple' => TRUE,
      'weight' => [
        'form' => 30,
        'view' => 30,
      ],
    ];
    $fields['group'] = $this->farmFieldFactory->baseFieldDefinition($options);

    return $fields;
  }

}
