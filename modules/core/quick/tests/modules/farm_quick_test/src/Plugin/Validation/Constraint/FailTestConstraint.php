<?php

declare(strict_types=1);

namespace Drupal\farm_quick_test\Plugin\Validation\Constraint;

use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\Core\Validation\Attribute\Constraint;
use Symfony\Component\Validator\Constraint as SymfonyConstraint;

/**
 * Fail validation if the field is TRUE.
 */
#[Constraint(
  id: 'FailTest',
  label: new TranslatableMarkup('Fail test', ['context' => 'Validation']),
)]
class FailTestConstraint extends SymfonyConstraint {

  /**
   * The default violation message.
   *
   * @var string
   */
  public $message = 'Fail!';

}
