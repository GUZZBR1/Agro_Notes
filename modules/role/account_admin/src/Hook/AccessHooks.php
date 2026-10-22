<?php

declare(strict_types=1);

namespace Drupal\farm_account_admin\Hook;

use Drupal\Core\Access\AccessResult;
use Drupal\Core\Entity\EntityInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Session\AccountInterface;

/**
 * Access hook implementations for farm_account_admin.
 */
class AccessHooks {

  /**
   * Implements hook_ENTITY_TYPE_access().
   */
  #[Hook('user_access')]
  public function userAccess(EntityInterface $entity, $operation, AccountInterface $account) {

    // Only user 1 can access user 1.
    if ($entity->id() == 1 && $account->id() != 1) {
      return AccessResult::forbidden();
    }
    return AccessResult::neutral();
  }

}
