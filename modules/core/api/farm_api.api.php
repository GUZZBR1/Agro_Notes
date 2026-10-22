<?php

/**
 * @file
 * Hooks provided by farm_api.
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
 * Alter the a "meta.farm" data in the root /api endpoint.
 *
 * @param array &$data
 *   The data to be altered.
 */
function hook_farm_api_meta_alter(array &$data) {

  // Add a custom key.
  $data['mykey'] = 'myvalue';
}

/**
 * Allow entity types to be included in JSON:API resources.
 *
 * @return string[]
 *   Returns an array of entity type IDs.
 */
function hook_farm_api_allow_resource_types() {

  // Allow block and view entities.
  return ['block', 'view'];
}

/**
 * Alter allowed entity types to be included in JSON:API resources.
 *
 * @param string[] $entity_types
 *   An array of entity type IDs allowed by other modules.
 */
function hook_farm_api_allow_resource_types_alter(&$entity_types) {

  // Disable view entities.
  if (in_array('view', $entity_types)) {
    unset($entity_types[array_search('view', $entity_types)]);
  }
}

/**
 * @} End of "addtogroup hooks".
 */
