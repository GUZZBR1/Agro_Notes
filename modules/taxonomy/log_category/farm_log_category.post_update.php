<?php

/**
 * @file
 * Update hooks for farm_log_category.module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function farm_log_category_removed_post_updates() {
  return [
    'farm_log_category_post_update_create_log_categorize_action' => '4.x',
  ];
}
