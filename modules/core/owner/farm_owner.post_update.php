<?php

/**
 * @file
 * Updates farm_owner module.
 */

declare(strict_types=1);

use Drupal\system\Entity\Action;

/**
 * Add owner field to plans.
 */
function farm_owner_post_update_add_plan_owner(&$sandbox = NULL) {
  if (\Drupal::moduleHandler()->moduleExists('plan')) {
    $entity_type = 'plan';
    $module_name = 'farm_owner';
    $field_name = 'owner';

    $field_info = [
      'type' => 'entity_reference',
      'label' => t('Owner'),
      'description' => t('Assign ownership to one or more users.'),
      'target_type' => 'user',
      'multiple' => TRUE,
      'weight' => [
        'form' => -70,
        'view' => -70,
      ],
    ];
    $field_definition = \Drupal::service('farm_field.factory')->baseFieldDefinition($field_info);
    \Drupal::entityDefinitionUpdateManager()
      ->installFieldStorageDefinition($field_name, $entity_type, $module_name, $field_definition);

    // Create action for assigning plans to users.
    $action = Action::create([
      'id' => 'plan_assign_action',
      'label' => t('Assign owners'),
      'type' => 'plan',
      'plugin' => 'plan_assign_action',
      'configuration' => [],
    ]);
    $action->save();
  }
}

/**
 * Implements hook_removed_post_updates().
 */
function farm_owner_removed_post_updates() {
  return [
    'farm_owner_post_update_add_asset_owner' => '4.x',
  ];
}
