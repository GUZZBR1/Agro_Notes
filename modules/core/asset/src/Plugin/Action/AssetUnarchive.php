<?php

declare(strict_types=1);

namespace Drupal\asset\Plugin\Action;

use Drupal\Core\Action\Attribute\Action;
use Drupal\Core\Action\Plugin\Action\EntityActionBase;
use Drupal\Core\Session\AccountInterface;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\asset\Entity\AssetInterface;

/**
 * Action that unarchives an asset.
 */
#[Action(
  id: 'asset_unarchive_action',
  label: new TranslatableMarkup('Unarchive an Asset'),
  type: 'asset',
)]
class AssetUnarchive extends EntityActionBase {

  /**
   * {@inheritdoc}
   */
  public function execute(?AssetInterface $asset = NULL) {

    // Bail if there is no asset.
    if (empty($asset)) {
      return;
    }

    // Unarchive the asset if it is archived.
    $archived = $asset->get('archived')->value;
    if ($archived) {
      $asset->set('archived', FALSE);
      $asset->setNewRevision(TRUE);
      $asset->setRevisionLogMessage($this->t('Unarchived')->render());
      $asset->save();
    }
  }

  /**
   * {@inheritdoc}
   */
  public function access($object, ?AccountInterface $account = NULL, $return_as_object = FALSE) {
    /** @var \Drupal\asset\Entity\AssetInterface $object */
    // Check entity and archived field access.
    $result = $object->get('archived')->access('edit', $account, TRUE)
      ->andIf($object->access('update', $account, TRUE));
    return $return_as_object ? $result : $result->isAllowed();
  }

}
