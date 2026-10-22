<?php

declare(strict_types=1);

namespace Drupal\plan\Plugin\Action;

use Drupal\Core\Action\Attribute\Action;
use Drupal\Core\Action\Plugin\Action\EntityActionBase;
use Drupal\Core\Session\AccountInterface;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\plan\Entity\PlanInterface;

/**
 * Action that archives a plan.
 */
#[Action(
  id: 'plan_archive_action',
  label: new TranslatableMarkup('Archive a plan'),
  type: 'plan',
)]
class PlanArchive extends EntityActionBase {

  /**
   * {@inheritdoc}
   */
  public function execute(?PlanInterface $plan = NULL) {

    // Bail if there is no plan.
    if (empty($plan)) {
      return;
    }

    // Archive the plan if it isn't already.
    $archived = $plan->get('archived')->value;
    if (!$archived) {
      $plan->set('archived', TRUE);
      $plan->setNewRevision(TRUE);
      $plan->setRevisionLogMessage($this->t('Archived')->render());
      $plan->save();
    }
  }

  /**
   * {@inheritdoc}
   */
  public function access($object, ?AccountInterface $account = NULL, $return_as_object = FALSE) {
    /** @var \Drupal\plan\Entity\PlanInterface $object */
    // Check entity and archived field access.
    $result = $object->get('archived')->access('edit', $account, TRUE)
      ->andIf($object->access('update', $account, TRUE));
    return $return_as_object ? $result : $result->isAllowed();
  }

}
