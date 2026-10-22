<?php

declare(strict_types=1);

namespace Drupal\farm_farm\Plugin\Validation\Constraint;

use Drupal\log\Entity\LogInterface;
use Symfony\Component\Validator\Constraint;
use Symfony\Component\Validator\ConstraintValidator;

/**
 * Validates the LogAssetFarm constraint.
 */
class LogAssetFarmValidator extends ConstraintValidator {

  /**
   * Log asset reference fields.
   *
   * @var string[]
   */
  protected array $fieldNames = [
    'asset',
    'equipment',
    'group',
    'location',
  ];

  /**
   * {@inheritdoc}
   */
  public function validate(mixed $value, Constraint $constraint) {
    /** @var \Drupal\log\Entity\LogInterface $value */
    /** @var \Drupal\farm_farm\Plugin\Validation\Constraint\LogAssetFarm $constraint */

    // If multiple unique farm IDs are referenced, add a violation.
    if (count($this->logReferencedAssetFarmIds($value)) > 1) {
      $this->context->addViolation($constraint->message);
    }
  }

  /**
   * Get a list of all the farm IDs that referenced assets are assigned to.
   *
   * @param \Drupal\log\Entity\LogInterface $log
   *   The log entity.
   *
   * @return int[]
   *   Returns an array of unique farm IDs. If an asset is not in a farm, an ID
   *   of 0 will be included in the list.
   */
  protected function logReferencedAssetFarmIds(LogInterface $log) {

    // Build a list of asset entity reference field items.
    /** @var \Drupal\Core\Field\EntityReferenceFieldItemListInterface[] $asset_refs */
    $asset_refs = [];

    // Consider direct asset references.
    foreach ($this->fieldNames as $name) {
      if ($log->hasField($name)) {
        $asset_refs[] = $log->get($name);
      }
    }

    // Consider inventory adjustment asset references.
    if ($log->hasField('quantity') && !$log->get('quantity')->isEmpty()) {
      foreach ($log->get('quantity')->referencedEntities() as $quantity) {
        /** @var \Drupal\quantity\Entity\QuantityInterface $quantity */
        if ($quantity->hasField('inventory_asset')) {
          $asset_refs[] = $quantity->get('inventory_asset');
        }
      }
    }

    // Accumulate the farm ids from all referenced assets.
    $farm_ids = [];
    foreach ($asset_refs as $asset_ref) {
      if ($asset_ref->isEmpty()) {
        continue;
      }
      foreach ($asset_ref->referencedEntities() as $asset) {
        /** @var \Drupal\asset\Entity\AssetInterface $asset */
        if ($asset->get('farm')->isEmpty()) {
          $farm_ids[] = 0;
        }
        else {
          foreach ($asset->get('farm')->referencedEntities() as $farm) {
            $farm_ids[] = $farm->id();
          }
        }
      }
    }

    // Return all unique farm IDs.
    return array_unique($farm_ids);
  }

}
