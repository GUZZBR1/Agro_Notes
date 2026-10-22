<?php

declare(strict_types=1);

namespace Drupal\farm_setup\Attribute;

use Drupal\Component\Plugin\Attribute\Plugin;
use Drupal\Core\StringTranslation\TranslatableMarkup;

/**
 * The setup form plugin attribute.
 */
#[\Attribute(\Attribute::TARGET_CLASS)]
class SetupForm extends Plugin {

  public function __construct(
    public readonly string $id,
    public readonly TranslatableMarkup $title,
    public readonly TranslatableMarkup $task_title,
    public readonly ?TranslatableMarkup $description = NULL,
    public readonly int $weight = 0,
  ) {}

}
