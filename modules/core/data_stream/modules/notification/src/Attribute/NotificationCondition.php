<?php

declare(strict_types=1);

namespace Drupal\data_stream_notification\Attribute;

use Drupal\Component\Plugin\Attribute\Plugin;
use Drupal\Core\StringTranslation\TranslatableMarkup;

/**
 * The Notification Condition plugin attribute.
 */
#[\Attribute(\Attribute::TARGET_CLASS)]
class NotificationCondition extends Plugin {

  public function __construct(
    public readonly string $id,
    public readonly TranslatableMarkup $label,
    public readonly array $context_definitions = [],
  ) {}

}
