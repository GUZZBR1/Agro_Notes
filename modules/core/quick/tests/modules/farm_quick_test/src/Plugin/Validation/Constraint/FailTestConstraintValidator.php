<?php

declare(strict_types=1);

namespace Drupal\farm_quick_test\Plugin\Validation\Constraint;

use Symfony\Component\Validator\Constraint;
use Symfony\Component\Validator\ConstraintValidator;

/**
 * Validates the FailTest constraint.
 */
class FailTestConstraintValidator extends ConstraintValidator {

  /**
   * {@inheritdoc}
   */
  public function validate($value, Constraint $constraint) {
    /** @var \Drupal\Core\Field\FieldItemListInterface $value */
    /** @var \Drupal\farm_quick_test\Plugin\Validation\Constraint\FailTestConstraint $constraint */
    if ($value->value === TRUE) {
      $this->context->addViolation($constraint->message);
    }
  }

}
