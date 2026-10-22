<?php

declare(strict_types=1);

namespace Drupal\farm_farm\Plugin\Validation\Constraint;

use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\Core\Validation\Attribute\Constraint;
use Symfony\Component\Validator\Constraint as SymfonyConstraint;

/**
 * Checks that assets are in the same farm as their parents.
 */
#[Constraint(
  id: 'AssetParentFarm',
  label: new TranslatableMarkup('Assets are in the same farm as their parents', ['context' => 'Validation']),
)]
class AssetParentFarm extends SymfonyConstraint {

  /**
   * The default violation message.
   *
   * @var string
   */
  public string $message = 'Assets must be in the same farm as their parents.';

}
