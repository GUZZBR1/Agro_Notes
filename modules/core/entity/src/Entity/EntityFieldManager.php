<?php

declare(strict_types=1);

namespace Drupal\farm_entity\Entity;

use Drupal\Core\Entity\EntityFieldManager as CoreEntityFieldManager;

/**
 * Extends the Drupal core EntityFieldManager service.
 *
 * Temporarily adds the rebuildBundleFieldMap() method until farmOS 5.x.
 *
 * @deprecated in farm:4.0.2 and is removed from farm:5.0.0. No replacement is
 *   necessary.
 * @see https://www.drupal.org/node/3591108
 */
class EntityFieldManager extends CoreEntityFieldManager {

  /**
   * This is a no-op method to maintain backwards compatibility in farmOS 4.x.
   *
   * @deprecated in farm:4.0.2 and is removed from farm:5.0.0. No replacement is
   *   necessary.
   * @see https://www.drupal.org/node/3591108
   */
  public function rebuildBundleFieldMap() {
    @trigger_error('EntityFieldManager::rebuildBundleFieldMap() is deprecated in farm:4.0.2 and is removed from farm:5.0.0. No replacement is necessary. See https://www.drupal.org/node/3591108', E_USER_DEPRECATED);
  }

}
