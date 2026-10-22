<?php

declare(strict_types=1);

namespace Drupal\farm_farm\Plugin\Validation\Constraint;

use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\DependencyInjection\ContainerInjectionInterface;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Symfony\Component\Validator\Constraint;
use Symfony\Component\Validator\ConstraintValidator;

/**
 * Validates the AssetParentFarm constraint.
 */
class AssetParentFarmValidator extends ConstraintValidator implements ContainerInjectionInterface {

  use AutowireTrait;

  public function __construct(
    protected EntityTypeManagerInterface $entityTypeManager,
  ) {}

  /**
   * {@inheritdoc}
   */
  public function validate(mixed $value, Constraint $constraint) {
    /** @var \Drupal\Core\Field\EntityReferenceFieldItemList $value */
    /** @var \Drupal\farm_farm\Plugin\Validation\Constraint\AssetParentFarm $constraint */

    // Load the asset.
    /** @var \Drupal\asset\Entity\AssetInterface|null $asset */
    $asset = $value->getParent()->getValue();
    if (is_null($asset)) {
      return;
    }

    // Load the asset's farm ID.
    $farm_ids = array_map(function ($farm) {
      return $farm->id();
    }, $asset->get('farm')->referencedEntities());
    $farm_id = reset($farm_ids);

    // Load all related parent and child assets.
    $relations = $asset->get('parent')->referencedEntities();
    $asset_storage = $this->entityTypeManager->getStorage('asset');
    $children_ids = $asset_storage
      ->getQuery()
      ->accessCheck(FALSE)
      ->condition('parent', $asset->id())
      ->execute();
    $relations += $asset_storage->loadMultiple($children_ids);

    // Ensure that all assets are in the same farm.
    $violation = FALSE;
    /** @var \Drupal\asset\Entity\AssetInterface[] $relations */
    foreach ($relations as $relation) {

      // If the relation is in one or more farms, load the farm ID and compare
      // it to the asset. If they don't match, add a violation.
      if (!$relation->get('farm')->isEmpty()) {
        $relation_farm_ids = array_map(function ($farm) {
          return $farm->id();
        }, $relation->get('farm')->referencedEntities());
        $relation_farm_id = reset($relation_farm_ids);
        if ($farm_id != $relation_farm_id) {
          $violation = TRUE;
          break;
        }
      }

      // Or, if the relation isn't in a farm, but the asset is, add a violation.
      elseif (!empty($farm_id)) {
        $violation = TRUE;
        break;
      }
    }
    if ($violation) {
      $this->context->addViolation($constraint->message);
    }
  }

}
