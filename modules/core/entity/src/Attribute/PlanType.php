<?php

declare(strict_types=1);

namespace Drupal\farm_entity\Attribute;

use Drupal\Component\Plugin\Attribute\Plugin;
use Drupal\Core\StringTranslation\TranslatableMarkup;

/**
 * The Plan Type plugin attribute.
 */
#[\Attribute(\Attribute::TARGET_CLASS)]
class PlanType extends Plugin {

  public function __construct(
    public readonly string $id,
    public readonly TranslatableMarkup $label,
  ) {}

}
