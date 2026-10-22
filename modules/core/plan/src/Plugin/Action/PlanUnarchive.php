<?php

declare(strict_types=1);

namespace Drupal\plan\Plugin\Action;

use Drupal\Core\Action\Attribute\Action;
use Drupal\Core\Action\Plugin\Action\EntityActionBase;
use Drupal\Core\Session\AccountInterface;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\plan\Entity\PlanInterface;

/**
 * Action that unarchives a plan.
 */
#[Action(
  id: 'plan_unarchive_action',
  label: new TranslatableMarkup('Unarchive a plan'),
  type: 'plan',
)]
class PlanUnarchive extends EntityActionBase {

  /**
   * {@inheritdoc}
   */
  public function execute(?PlanInterface $plan = NULL) {

    // Bail if there is no plan.
    if (empty($plan)) {
      return;
    }

    // Unarchive the plan if it is archived.
    $archived = $plan->get('archived')->value;
    if ($archived) {
      $plan->set('archived', FALSE);
      $plan->setNewRevision(TRUE);
      $plan->setRevisionLogMessage($this->t('Unarchived')->render());
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
