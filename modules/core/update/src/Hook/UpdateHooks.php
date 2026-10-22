<?php

declare(strict_types=1);

namespace Drupal\farm_update\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\farm_update\FarmUpdateInterface;

/**
 * Update hook implementations for farm_update.
 */
class UpdateHooks {

  public function __construct(
    protected FarmUpdateInterface $farmUpdate,
  ) {}

  /**
   * Implements hook_rebuild().
   */
  #[Hook('rebuild')]
  public function rebuild() {
    $this->farmUpdate->rebuild();
  }

}
