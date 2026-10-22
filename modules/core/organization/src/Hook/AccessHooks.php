<?php

declare(strict_types=1);

namespace Drupal\organization\Hook;

use Drupal\Core\Access\AccessResult;
use Drupal\Core\Access\AccessResultInterface;
use Drupal\Core\Entity\EntityInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Session\AccountInterface;

/**
 * Access hook implementations for organization.
 */
class AccessHooks {

  /**
   * Implements hook_entity_access().
   */
  #[Hook('entity_access')]
  public function entityAccess(EntityInterface $entity, $operation, AccountInterface $account): AccessResultInterface {

    // Default to neutral.
    $access = AccessResult::neutral();

    // We only care about organization entities.
    if ($entity->getEntityTypeId() !== 'organization') {
      return $access;
    }

    // Allow access to view revisions if the user has "view all organization
    // revisions" permission.
    if (in_array($operation, ['view revision', 'view all revisions'])) {
      $access = AccessResult::allowedIfHasPermission($account, 'view all organization revisions');
    }

    // Allow access to revert revisions if the user has "revert all organization
    // revisions" permission.
    if ($operation === 'revert') {
      $access = AccessResult::allowedIfHasPermission($account, 'revert all organization revisions');
    }

    // Return the access result.
    return $access;
  }

}
