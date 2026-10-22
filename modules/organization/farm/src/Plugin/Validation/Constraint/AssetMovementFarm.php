<?php

declare(strict_types=1);

namespace Drupal\farm_farm\Plugin\Validation\Constraint;

use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\Core\Validation\Attribute\Constraint;
use Symfony\Component\Validator\Constraint as SymfonyConstraint;

/**
 * Checks that asset farm cannot be changed when movement logs exist.
 */
#[Constraint(
  id: 'AssetMovementFarm',
  label: new TranslatableMarkup('Asset farm association cannot be changed when movement logs exist', ['context' => 'Validation']),
)]
class AssetMovementFarm extends SymfonyConstraint {

  /**
   * The default violation message.
   *
   * @var string
   */
  public string $message = 'The farm that an asset is associated with cannot be changed if there are movement logs that reference the asset.';

}
