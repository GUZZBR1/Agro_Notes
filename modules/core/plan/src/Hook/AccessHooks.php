<?php

declare(strict_types=1);

namespace Drupal\plan\Hook;

use Drupal\Core\Access\AccessResult;
use Drupal\Core\Access\AccessResultInterface;
use Drupal\Core\Entity\EntityInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Session\AccountInterface;

/**
 * Access hook implementations for plan.
 */
class AccessHooks {

  /**
   * Implements hook_entity_access().
   */
  #[Hook('entity_access')]
  public function entityAccess(EntityInterface $entity, $operation, AccountInterface $account): AccessResultInterface {

    // Default to neutral.
    $access = AccessResult::neutral();

    // We only care about plan entities.
    if ($entity->getEntityTypeId() !== 'plan') {
      return $access;
    }

    // Allow access to view revisions if the user has "view all plan revisions"
    // permission.
    if (in_array($operation, ['view revision', 'view all revisions'])) {
      $access = AccessResult::allowedIfHasPermission($account, 'view all plan revisions');
    }

    // Allow access to revert revisions if the user has "revert all plan
    // revisions" permission.
    if ($operation === 'revert') {
      $access = AccessResult::allowedIfHasPermission($account, 'revert all plan revisions');
    }

    // Return the access result.
    return $access;
  }

}
