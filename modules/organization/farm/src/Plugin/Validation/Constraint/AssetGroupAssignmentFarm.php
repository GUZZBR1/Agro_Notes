<?php

declare(strict_types=1);

namespace Drupal\farm_farm\Plugin\Validation\Constraint;

use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\Core\Validation\Attribute\Constraint;
use Symfony\Component\Validator\Constraint as SymfonyConstraint;

/**
 * Checks that asset group cannot be changed when group assignment logs exist.
 */
#[Constraint(
  id: 'AssetGroupAssignmentFarm',
  label: new TranslatableMarkup('Asset farm association cannot be changed when group assignment logs exist', ['context' => 'Validation']),
)]
class AssetGroupAssignmentFarm extends SymfonyConstraint {

  /**
   * The default violation message.
   *
   * @var string
   */
  public string $message = 'The farm that an asset is associated with cannot be changed if there are group assignment logs that reference the asset.';

}
