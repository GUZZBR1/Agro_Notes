<?php

declare(strict_types=1);

namespace Drupal\data_stream_notification\Annotation;

use Drupal\Component\Annotation\Plugin;

/**
 * Defines a notification condition annotation object.
 *
 * @deprecated in farm:4.0.0 and is removed from farm:5.0.0.
 *   Use Attributes moving forward.
 * @see https://www.drupal.org/node/3523485
 * @see https://www.drupal.org/project/farm/issues/3461548
 *
 * @Annotation
 */
class NotificationCondition extends Plugin {

  /**
   * The condition ID.
   *
   * @var string
   */
  public $id;

  /**
   * The condition label.
   *
   * @var \Drupal\Core\Annotation\Translation
   *
   * @ingroup plugin_translatable
   */
  public $label;

}
