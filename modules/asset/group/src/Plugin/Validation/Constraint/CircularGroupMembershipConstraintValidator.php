<?php

declare(strict_types=1);

namespace Drupal\farm_group\Plugin\Validation\Constraint;

use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\DependencyInjection\ContainerInjectionInterface;
use Drupal\asset\Entity\AssetInterface;
use Drupal\farm_group\GroupMembershipInterface;
use Symfony\Component\Validator\Constraint;
use Symfony\Component\Validator\ConstraintValidator;

/**
 * Validates the CircularGroupMembership constraint.
 */
class CircularGroupMembershipConstraintValidator extends ConstraintValidator implements ContainerInjectionInterface {

  use AutowireTrait;

  public function __construct(
    protected GroupMembershipInterface $groupMembership,
  ) {}

  /**
   * {@inheritdoc}
   */
  public function validate($value, Constraint $constraint) {
    /** @var \Drupal\Core\Field\EntityReferenceFieldItemList $value */
    /** @var \Drupal\farm_group\Plugin\Validation\Constraint\CircularGroupMembershipConstraint $constraint */

    // Get the log that this field is on.
    $log = $value->getParent()->getValue();

    // If the log is not a group assignment, we have nothing to validate.
    if (empty($log->get('is_group_assignment')->value)) {
      return;
    }

    // Get the group(s) that asset(s) are being made members of.
    $groups = $log->get('group')->referencedEntities();

    // If there are no groups, we have nothing to validate.
    if (empty($groups)) {
      return;
    }

    // Get the log's timestamp.
    $timestamp = $log->get('timestamp')->value;

    // Iterate through referenced entities.
    foreach ($value->referencedEntities() as $delta => $asset) {

      // If this asset is not a group, skip it.
      if ($asset->bundle() != 'group') {
        continue;
      }

      // Load members of this group (recursively).
      assert($asset instanceof AssetInterface);
      $members = $this->groupMembership->getGroupMembers([$asset], TRUE, $timestamp);

      // Iterate through the groups and look for violations.
      $violation = FALSE;
      foreach ($groups as $group) {

        // Make sure that the asset and group are not the same.
        if ($group->id() == $asset->id()) {
          $violation = TRUE;
        }

        // Make sure that none of the group(s) are members of this asset.
        foreach ($members as $member) {
          if ($group->id() == $member->id()) {
            $violation = TRUE;
            break;
          }
        }
      }

      // If a violation was found, flag it.
      if ($violation) {
        $this->context->buildViolation($constraint->message, ['%asset' => $asset->label()])
          ->atPath((string) $delta . '.target_id')
          ->setInvalidValue($asset->id())
          ->addViolation();
      }
    }
  }

}
