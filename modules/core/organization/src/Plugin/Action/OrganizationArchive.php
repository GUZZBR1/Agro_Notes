<?php

declare(strict_types=1);

namespace Drupal\organization\Plugin\Action;

use Drupal\Core\Action\Attribute\Action;
use Drupal\Core\Action\Plugin\Action\EntityActionBase;
use Drupal\Core\Session\AccountInterface;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\organization\Entity\OrganizationInterface;

/**
 * Action that archives an organization.
 */
#[Action(
  id: 'organization_archive_action',
  label: new TranslatableMarkup('Archive an organization'),
  type: 'organization',
)]
class OrganizationArchive extends EntityActionBase {

  /**
   * {@inheritdoc}
   */
  public function execute(?OrganizationInterface $organization = NULL) {

    // Bail if there is no organization.
    if (empty($organization)) {
      return;
    }

    // Archive the organization if it isn't already.
    $archived = $organization->get('archived')->value;
    if (!$archived) {
      $organization->set('archived', TRUE);
      $organization->setNewRevision(TRUE);
      $organization->setRevisionLogMessage($this->t('Archived')->render());
      $organization->save();
    }
  }

  /**
   * {@inheritdoc}
   */
  public function access($object, ?AccountInterface $account = NULL, $return_as_object = FALSE) {
    /** @var \Drupal\organization\Entity\OrganizationInterface $object */
    // Check entity and archived field access.
    $result = $object->get('archived')->access('edit', $account, TRUE)
      ->andIf($object->access('update', $account, TRUE));
    return $return_as_object ? $result : $result->isAllowed();
  }

}
