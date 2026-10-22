<?php

/**
 * @file
 * Post update functions for Data Stream Notifications module.
 */

declare(strict_types=1);

/**
 * Implements hook_removed_post_updates().
 */
function data_stream_notification_removed_post_updates() {
  return [
    'data_stream_notification_post_update_enable_farm_notification' => '4.x',
  ];
}
