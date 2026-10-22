<?php

declare(strict_types=1);

namespace Drupal\farm_log_quantity\Hook;

use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\log\Entity\LogInterface;
use Drupal\quantity\Entity\QuantityInterface;

/**
 * Entity hook implementations for farm_log_quantity.
 */
class EntityHooks {

  use StringTranslationTrait;

  public function __construct(
    protected EntityTypeManagerInterface $entityTypeManager,
  ) {}

  /**
   * Implements hook_ENTITY_TYPE_delete().
   */
  #[Hook('log_delete')]
  public function logDelete(LogInterface $log) {

    // If the log doesn't have a quantity field, bail.
    if (!$log->hasField('quantity')) {
      return;
    }

    // Get any quantities the log references.
    $quantities = $log->get('quantity')->referencedEntities();

    // Delete quantity entities.
    if (!empty($quantities)) {
      $this->entityTypeManager->getStorage('quantity')->delete($quantities);
    }
  }

  /**
   * Implements hook_ENTITY_TYPE_delete().
   */
  #[Hook('quantity_delete')]
  public function quantityDelete(QuantityInterface $quantity) {

    // Look up logs that reference the quantity.
    $log_storage = $this->entityTypeManager->getStorage('log');
    $query = $log_storage->getQuery();
    $query->condition('quantity.target_id', $quantity->id());
    $query->accessCheck(FALSE);
    $log_ids = $query->execute();
    /** @var \Drupal\log\Entity\LogInterface[] $logs */
    $logs = [];
    if (!empty($log_ids)) {
      $logs = $log_storage->loadMultiple($log_ids);
    }

    // Remove references to the quantity from the log and save a revision.
    foreach ($logs as $log) {
      $log->set('quantity', array_filter($log->get('quantity')->getValue(), function ($value) use ($quantity) {
        if (!empty($value['target_id']) && $value['target_id'] == $quantity->id()) {
          return FALSE;
        }
        return TRUE;
      }));
      $log->setNewRevision(TRUE);
      $log->setRevisionLogMessage($this->t('Removed reference to deleted quantity %uuid.', ['%uuid' => $quantity->uuid()])->render());
      $log->save();
    }
  }

}
