<?php

declare(strict_types=1);

namespace Drupal\farm_structure\Entity;

use Drupal\Core\Config\Entity\ConfigEntityInterface;

/**
 * Provides an interface for defining FarmStructureType config entities.
 *
 * @ingroup farm
 */
interface FarmStructureTypeInterface extends ConfigEntityInterface {

  /**
   * Returns the structure type label.
   *
   * @return string
   *   The structure type label.
   */
  public function getLabel();

}
