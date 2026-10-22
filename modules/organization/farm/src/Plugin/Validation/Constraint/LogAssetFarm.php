<?php

declare(strict_types=1);

namespace Drupal\farm_farm\Plugin\Validation\Constraint;

use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\Core\Validation\Attribute\Constraint;
use Symfony\Component\Validator\Constraint as SymfonyConstraint;

/**
 * Checks that all assets referenced by a log are in the same farm.
 */
#[Constraint(
  id: 'LogAssetFarm',
  label: new TranslatableMarkup('Logs can only reference assets in the same farm', ['context' => 'Validation']),
)]
class LogAssetFarm extends SymfonyConstraint {

  /**
   * The default violation message.
   *
   * @var string
   */
  public string $message = 'All assets referenced by a log must be in the same farm.';

}
