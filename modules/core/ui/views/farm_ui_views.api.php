<?php

/**
 * @file
 * Hooks provided by farm_ui_views.
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
 * Defines base fields that should be added to farmOS Views.
 *
 * @param string $entity_type
 *   The entity type machine name.
 *
 * @return array
 *   Returns an array of base field machine names for a given entity type.
 */
function hook_farm_ui_views_base_fields(string $entity_type) {
  $base_fields = [];

  // Add my base field to farmOS asset Views.
  if ($entity_type == 'asset') {
    $base_fields[] = 'mybasefield';
  }

  return $base_fields;
}

/**
 * @} End of "addtogroup hooks".
 */
