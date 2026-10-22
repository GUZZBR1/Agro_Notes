<?php

declare(strict_types=1);

namespace Drupal\farm_farm\Plugin\Validation\Constraint;

use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\DependencyInjection\ContainerInjectionInterface;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Symfony\Component\Validator\Constraint;
use Symfony\Component\Validator\ConstraintValidator;

/**
 * Validates the AssetMovementFarm constraint.
 */
class AssetMovementFarmValidator extends ConstraintValidator implements ContainerInjectionInterface {

  use AutowireTrait;

  public function __construct(
    protected EntityTypeManagerInterface $entityTypeManager,
  ) {}

  /**
   * {@inheritdoc}
   */
  public function validate(mixed $value, Constraint $constraint) {
    /** @var \Drupal\Core\Field\EntityReferenceFieldItemList $value */
    /** @var \Drupal\farm_farm\Plugin\Validation\Constraint\AssetMovementFarm $constraint */

    // Get the asset entity.
    /** @var \Drupal\asset\Entity\AssetInterface|null $asset */
    $asset = $value->getParent()->getValue();
    if (is_null($asset)) {
      return;
    }

    // If the asset is new, bail.
    if ($asset->isNew()) {
      return;
    }

    // Load the original unchanged asset from the database.
    $original_asset = $this->entityTypeManager->getStorage('asset')->load($asset->id());

    // Only proceed if the farm field has changed.
    if ($asset->get('farm')->target_id == $original_asset->get('farm')->target_id) {
      return;
    }

    // If there are any movement logs that reference the asset (in either the
    // asset or location field), add a violation.
    /** @var \Drupal\Core\Entity\Query\QueryInterface $query */
    $query = $this->entityTypeManager->getStorage('log')->getQuery();
    $condition = $query
      ->orConditionGroup()
      ->condition('asset', $asset->id())
      ->condition('location', $asset->id());
    $log_ids = $query
      ->accessCheck(FALSE)
      ->condition('is_movement', TRUE)
      ->condition($condition)
      ->execute();
    if (!empty($log_ids)) {
      $this->context->addViolation($constraint->message);
    }
  }

}
