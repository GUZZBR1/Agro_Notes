<?php

declare(strict_types=1);

namespace Drupal\farm_update;

/**
 * Farm update service interface.
 *
 * @internal
 */
interface FarmUpdateInterface {

  /**
   * Rebuild farmOS configuration.
   */
  public function rebuild(): void;

}
