<?php

/**
 * @file
 * Hooks provided by farm_import_csv.
 *
 * This file contains no working PHP code; it exists to provide additional
 * documentation for doxygen as well as to document hooks in the standard
 * Drupal manner.
 */

declare(strict_types=1);

/**
 * @addtogroup hooks
 * @{
 */

/**
 * Defines base fields that should be added to default CSV importers.
 *
 * @param string $entity_type
 *   The entity type machine name.
 *
 * @return array
 *   Returns an array of base field machine names for a given entity type.
 */
function hook_farm_import_csv_base_fields(string $entity_type) {
  $base_fields = [];

  // Add my base field to asset CSV importers.
  if ($entity_type == 'asset') {
    $base_fields[] = 'mybasefield';
  }

  return $base_fields;
}

/**
 * Excludes fields from default CSV importers.
 *
 * @param string $entity_type
 *   The entity type machine name.
 *
 * @return array
 *   Returns an array of field machine names to exclude from the entity type.
 */
function hook_farm_import_csv_exclude_fields(string $entity_type) {
  $exclude_fields = [];

  // Exclude my custom field from asset CSV importers.
  if ($entity_type == 'asset') {
    $exclude_fields[] = 'mycustomfield';
  }

  return $exclude_fields;
}

/**
 * @} End of "addtogroup hooks".
 */
