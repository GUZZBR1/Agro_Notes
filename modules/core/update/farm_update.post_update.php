<?php

/**
 * @file
 * Post update functions for farm_update module.
 */

declare(strict_types=1);

/**
 * Remove farm_update.settings.excluded_config.
 */
function farm_update_post_update_remove_excluded_config(&$sandbox) {
  \Drupal::configFactory()->getEditable('farm_update.settings')->clear('excluded_config')->save();
}
