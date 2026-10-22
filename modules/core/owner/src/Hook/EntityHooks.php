<?php

declare(strict_types=1);

namespace Drupal\farm_owner\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Session\AccountInterface;
use Drupal\log\Entity\LogInterface;

/**
 * Entity hook implementations for farm_owner.
 */
class EntityHooks {

  public function __construct(
    protected AccountInterface $currentUser,
  ) {}

  /**
   * Implements hook_ENTITY_TYPE_presave().
   */
  #[Hook('log_presave')]
  public function logPresave(LogInterface $log) {

    // If there is no currently logged-in user, bail.
    if (empty($this->currentUser->id())) {
      return;
    }

    // If the log already has an owner, bail.
    $owners = $log->get('owner')->referencedEntities();
    if (!empty($owners)) {
      return;
    }

    // Add the current user to the log's owners.
    $log->set('owner', [$this->currentUser->id()]);
  }

}
