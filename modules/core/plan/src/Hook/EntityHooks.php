<?php

declare(strict_types=1);

namespace Drupal\plan\Hook;

use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\plan\Entity\PlanInterface;

/**
 * Entity hook implementations for plan.
 */
class EntityHooks {

  public function __construct(
    protected EntityTypeManagerInterface $entityTypeManager,
  ) {}

  /**
   * Implements hook_ENTITY_TYPE_delete().
   */
  #[Hook('plan_delete')]
  public function planDelete(PlanInterface $plan) {

    // Delete all plan_record entities associated with the plan.
    $plan_record_storage = $this->entityTypeManager->getStorage('plan_record');
    $plan_ids = $plan_record_storage->getQuery()
      ->condition('plan', $plan->id())
      ->accessCheck(FALSE)
      ->execute();
    if (count($plan_ids) < 1) {
      return;
    }
    foreach (array_chunk($plan_ids, 100) as $chunk) {
      $plan_records = $plan_record_storage->loadMultiple($chunk);
      $plan_record_storage->delete($plan_records);
    }
  }

}
