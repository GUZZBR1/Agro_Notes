<?php

declare(strict_types=1);

namespace Drupal\farm_quick\Attribute;

use Drupal\Component\Plugin\Attribute\Plugin;
use Drupal\Core\StringTranslation\TranslatableMarkup;

/**
 * The Quick Form plugin attribute.
 */
#[\Attribute(\Attribute::TARGET_CLASS)]
class QuickForm extends Plugin {

  public function __construct(
    public readonly string $id,
    public readonly TranslatableMarkup $label,
    public readonly ?TranslatableMarkup $description = NULL,
    public readonly ?TranslatableMarkup $helpText = NULL,
    public readonly array $permissions = [],
    public readonly bool $requiresEntity = FALSE,
  ) {}

}
